const express = require("express");
const router = express.Router();
const db = require("../db");
const http = require("http");

function calcularScore(data) {
    const ingreso = parseFloat(data.ingreso_mensual) || 0;
    const montoSolicitado = parseFloat(data.monto_solicitado) || 0;
    const plazo = parseInt(data.plazo) || 1;
    const cuotaEstimada = montoSolicitado / plazo;
    const deudasActuales = parseFloat(data.total_cuotas_mensuales) || 0;
    const capacidadPago = ingreso - (deudasActuales + cuotaEstimada);
    const nivelEndeudamiento = ingreso > 0 ? (deudasActuales / ingreso) * 100 : 100;

    const scoreCapacidad = capacidadPago > 0 ? Math.min(100, (capacidadPago / ingreso) * 100) : 0;
    const scoreEndeudamiento = Math.max(0, 100 - nivelEndeudamiento);
    const scoreHistorial = data.historial_pagos === "Bueno" ? 100 : data.historial_pagos === "Regular" ? 50 : data.historial_pagos === "Malo" ? 0 : 60;
    const scoreEstabilidad = data.antiguedad_laboral === "Mas de 2 años" ? 100 : data.antiguedad_laboral === "1-2 años" ? 70 : data.antiguedad_laboral === "6-12 meses" ? 40 : data.antiguedad_laboral === "Menos de 6 meses" ? 10 : 30;
    const scoreGarantia = data.tiene_garantia === "Sí" ? 100 : data.tiene_aval === "Sí" ? 60 : 0;

    const score = Math.round(
        scoreCapacidad * 0.30 +
        scoreEndeudamiento * 0.25 +
        scoreHistorial * 0.20 +
        scoreEstabilidad * 0.15 +
        scoreGarantia * 0.10
    );

    let clasificacion = "Alto Riesgo";
    if (score >= 85) clasificacion = "Excelente";
    else if (score >= 70) clasificacion = "Bueno";
    else if (score >= 55) clasificacion = "Regular";
    else if (score >= 40) clasificacion = "Riesgoso";

    let estado = "RECHAZADO";
    if (score >= 75 && data.historial_pagos !== "Malo") estado = "APROBADO";
    else if (score >= 60) estado = "REQUIERE EVALUACIÓN DEL ANALISTA";
    else if (score >= 40) estado = "REQUIERE MÁS REQUISITOS";

    let riesgo = "Alto";
    if (score >= 75) riesgo = "Bajo";
    else if (score >= 55) riesgo = "Moderado";

    return { score, clasificacion, capacidadPago, nivelEndeudamiento, riesgo, estado };
}

async function consultarML(data) {
    return new Promise((resolve) => {
        const postData = JSON.stringify({
            ingreso_mensual: parseFloat(data.ingreso_mensual) || 0,
            monto_solicitado: parseFloat(data.monto_solicitado) || 0,
            plazo: parseInt(data.plazo) || 1,
            edad: parseInt(data.edad) || 30,
            estado_civil: data.estado_civil || "Soltero",
            ocupacion: data.ocupacion || "",
            num_deudas_activas: parseInt(data.num_deudas_activas) || 0,
            tiene_garantia: data.tiene_garantia === "Sí" ? 1 : 0,
            historial_pagos: data.historial_pagos || "Regular"
        });

        const req = http.request({
            hostname: "127.0.0.1",
            port: 8502,
            path: "/api/predict",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(postData)
            },
            timeout: 5000
        }, (res) => {
            let body = "";
            res.on("data", chunk => body += chunk);
            res.on("end", () => {
                try {
                    resolve(JSON.parse(body));
                } catch (e) {
                    resolve(null);
                }
            });
        });

        req.on("error", () => resolve(null));
        req.on("timeout", () => { req.destroy(); resolve(null); });
        req.write(postData);
        req.end();
    });
}

router.post("/evaluar", async (req, res) => {
    try {
        const data = req.body;
        const analista = data.analista || req.headers["x-usuario"] || "Usuario";

        let result;

        if (data.resultado_ml) {
            const votosAprobado = (data.prediccion_knn === "APROBADO" ? 1 : 0) +
                                   (data.prediccion_id3 === "APROBADO" ? 1 : 0) +
                                   (data.prediccion_rf === "APROBADO" ? 1 : 0);
            const confianza = parseFloat(data.confianza_ml) || (votosAprobado / 3 * 100);

            let score = Math.round(confianza);
            let clasificacion = "Regular";
            if (score >= 85) clasificacion = "Excelente";
            else if (score >= 70) clasificacion = "Bueno";
            else if (score >= 55) clasificacion = "Regular";
            else if (score >= 40) clasificacion = "Riesgoso";
            else clasificacion = "Alto Riesgo";

            const ingreso = parseFloat(data.ingreso_mensual) || 0;
            const montoSolicitado = parseFloat(data.monto_solicitado) || 0;
            const plazo = parseInt(data.plazo) || 1;
            const cuotaEstimada = montoSolicitado / plazo;
            const deudasActuales = parseFloat(data.total_cuotas_mensuales) || 0;
            const capacidadPago = ingreso - (deudasActuales + cuotaEstimada);
            const nivelEndeudamiento = ingreso > 0 ? (deudasActuales / ingreso) * 100 : 100;

            let riesgo = "Alto";
            if (score >= 75) riesgo = "Bajo";
            else if (score >= 55) riesgo = "Moderado";

            result = {
                score, clasificacion, riesgo,
                capacidadPago, nivelEndeudamiento,
                estado: data.resultado_ml
            };
        } else {
            result = calcularScore(data);
        }

        let prediccionKnn = data.prediccion_knn || null;
        let prediccionId3 = data.prediccion_id3 || null;
        let prediccionRf = data.prediccion_rf || null;
        let confianzaMl = data.confianza_ml ? parseFloat(data.confianza_ml) : null;
        let recomendacionMl = data.recomendacion_ml || null;

        if (!data.resultado_ml) {
            try {
                const mlResult = await consultarML(data);
                if (mlResult) {
                    prediccionKnn = mlResult.knn || null;
                    prediccionId3 = mlResult.id3 || null;
                    prediccionRf = mlResult.random_forest || null;
                    if (mlResult.confianza) confianzaMl = parseFloat(mlResult.confianza);
                    if (mlResult.recomendacion) recomendacionMl = mlResult.recomendacion;
                }
            } catch (e) {}
        }

        const sql = `INSERT INTO evaluaciones_crediticias 
            (dni, cliente, edad, estado_civil, ocupacion, direccion, telefono,
             ingreso_mensual, antiguedad_laboral, monto_solicitado, plazo, tipo_credito,
             num_deudas_activas, total_cuotas_mensuales, tiene_aval, tiene_garantia,
             tipo_garantia, historial_pagos, capacidad_pago, nivel_endeudamiento,
             riesgo_estimado, score, clasificacion, estado, analista, observaciones,
             prediccion_knn, prediccion_id3, prediccion_rf, confianza_ml, recomendacion_ml)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`;

        const values = [
            data.dni, data.cliente, data.edad, data.estado_civil, data.ocupacion,
            data.direccion, data.telefono, data.ingreso_mensual, data.antiguedad_laboral,
            data.monto_solicitado, data.plazo, data.tipo_credito,
            data.num_deudas_activas, data.total_cuotas_mensuales, data.tiene_aval,
            data.tiene_garantia, data.tipo_garantia, data.historial_pagos,
            (result.capacidadPago || 0).toFixed(2), (result.nivelEndeudamiento || 0).toFixed(2),
            result.riesgo, result.score, result.clasificacion, result.estado,
            analista, data.observaciones || null,
            prediccionKnn, prediccionId3, prediccionRf,
            confianzaMl ? confianzaMl.toFixed(2) : null, recomendacionMl
        ];

        db.query(sql, values, (err, resultInsert) => {
            if (err) return res.status(500).json({ mensaje: "Error al guardar evaluación", error: err.sqlMessage });

            res.json({
                mensaje: "Evaluación completada",
                id: resultInsert.insertId,
                score: result.score,
                clasificacion: result.clasificacion,
                estado: result.estado,
                capacidad_pago: (result.capacidadPago || 0).toFixed(2),
                nivel_endeudamiento: (result.nivelEndeudamiento || 0).toFixed(2),
                riesgo: result.riesgo,
                ml: confianzaMl ? {
                    knn: prediccionKnn,
                    id3: prediccionId3,
                    random_forest: prediccionRf,
                    confianza: confianzaMl,
                    recomendacion: recomendacionMl
                } : null
            });
        });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

router.get("/aprobados", (req, res) => {
    const sql = `SELECT * FROM evaluaciones_crediticias 
                 WHERE estado = 'APROBADO' 
                 AND (usado_para_credito IS NULL OR usado_para_credito = 0)
                 ORDER BY id DESC LIMIT 100`;
    db.query(sql, (err, results) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta" });
        res.json(results);
    });
});

router.get("/pendientes", (req, res) => {
    const sql = `SELECT * FROM evaluaciones_crediticias 
                 WHERE estado LIKE 'REQUIERE%'
                 AND (usado_para_credito IS NULL OR usado_para_credito = 0)
                 ORDER BY id DESC LIMIT 100`;
    db.query(sql, (err, results) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta" });
        res.json(results);
    });
});

router.post("/efectuar-credito", (req, res) => {
    const { evaluacion_id, interes, frecuencia_pago, fecha_inicio, analista } = req.body;

    if (!evaluacion_id || !interes || !frecuencia_pago || !fecha_inicio) {
        return res.status(400).json({ mensaje: "Faltan datos: evaluación, interés, frecuencia y fecha son obligatorios" });
    }

    db.query("SELECT * FROM evaluaciones_crediticias WHERE id = ?", [evaluacion_id], (err, evals) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta", error: err.sqlMessage });
        if (evals.length === 0) return res.status(404).json({ mensaje: "Evaluación no encontrada" });

        const evalData = evals[0];

        if (evalData.estado !== "APROBADO") {
            return res.status(400).json({ mensaje: "Solicitud rechazada por evaluación crediticia. No cumple con la capacidad de pago mínima requerida." });
        }

        if (evalData.usado_para_credito) {
            return res.status(400).json({ mensaje: "Esta evaluación ya fue usada para un crédito anterior" });
        }

        const usuario = analista || "Sistema";

        db.query("SELECT id FROM clientes WHERE dni = ?", [evalData.dni], (err, clientes) => {
            if (err) return res.status(500).json({ mensaje: "Error de consulta", error: err.sqlMessage });

            const insertarCredito = (clienteId) => {
                const monto = parseFloat(evalData.monto_solicitado) || 0;
                const cuotas = parseInt(evalData.plazo) || 1;

                db.query(
                    `INSERT INTO creditos (cliente_id, monto, interes, cuotas, frecuencia_pago, fecha_inicio, estado)
                     VALUES (?, ?, ?, ?, ?, ?, 'Activo')`,
                    [clienteId, monto, interes, cuotas, frecuencia_pago, fecha_inicio],
                    (err, credResult) => {
                        if (err) return res.status(500).json({ mensaje: "Error al crear crédito", error: err.sqlMessage });

                        const creditoId = credResult.insertId;

                        const total = monto + (monto * interes / 100);
                        const montoCuota = total / cuotas;

                        const cuotasSql = [];
                        const cuotasParams = [];
                        for (let i = 1; i <= cuotas; i++) {
                            cuotasSql.push("(?, ?, ?, ?, 'Pendiente')");
                            cuotasParams.push(creditoId, i, montoCuota.toFixed(2), fecha_inicio);
                        }

                        db.query(
                            `INSERT INTO cronograma_pagos (credito_id, numero_cuota, monto_cuota, fecha_vencimiento, estado) VALUES ${cuotasSql.join(", ")}`,
                            cuotasParams,
                            (err) => {
                                if (err) return res.status(500).json({ mensaje: "Error al generar cronograma", error: err.sqlMessage });

                                db.query(
                                    "UPDATE evaluaciones_crediticias SET usado_para_credito = 1, credito_id = ?, fecha_desembolso = NOW() WHERE id = ?",
                                    [creditoId, evaluacion_id],
                                    (err) => {
                                        if (err) return res.status(500).json({ mensaje: "Error al actualizar evaluación", error: err.sqlMessage });

                                        res.json({
                                            mensaje: "Crédito efectuado correctamente",
                                            credito_id: creditoId,
                                            cliente_id: clienteId,
                                            monto: monto.toFixed(2),
                                            total: total.toFixed(2),
                                            monto_cuota: montoCuota.toFixed(2),
                                            cuotas: cuotas,
                                            frecuencia_pago: frecuencia_pago
                                        });
                                    }
                                );
                            }
                        );
                    }
                );
            };

            if (clientes.length > 0) {
                insertarCredito(clientes[0].id);
            } else {
                db.query(
                    "INSERT INTO clientes (dni, nombre, telefono, direccion) VALUES (?, ?, ?, ?)",
                    [evalData.dni, evalData.cliente, evalData.telefono || "", evalData.direccion || ""],
                    (err, cliResult) => {
                        if (err) return res.status(500).json({ mensaje: "Error al registrar cliente", error: err.sqlMessage });
                        insertarCredito(cliResult.insertId);
                    }
                );
            }
        });
    });
});

router.put("/:id/observaciones", (req, res) => {
    const { observaciones } = req.body;
    db.query(
        "UPDATE evaluaciones_crediticias SET observaciones = ? WHERE id = ?",
        [observaciones, req.params.id],
        (err) => {
            if (err) return res.status(500).json({ mensaje: "Error al actualizar" });
            res.json({ mensaje: "Observaciones actualizadas" });
        }
    );
});

router.get("/historial", (req, res) => {
    const { search, estado, desde, hasta, page = 1, limit = 50 } = req.query;
    const offset = (parseInt(page) - 1) * parseInt(limit);

    let sql = "SELECT * FROM evaluaciones_crediticias WHERE 1=1";
    let countSql = "SELECT COUNT(*) AS total FROM evaluaciones_crediticias WHERE 1=1";
    const params = [];
    const countParams = [];

    if (search) {
        const like = `%${search}%`;
        sql += " AND (dni LIKE ? OR cliente LIKE ? OR analista LIKE ?)";
        countSql += " AND (dni LIKE ? OR cliente LIKE ? OR analista LIKE ?)";
        params.push(like, like, like);
        countParams.push(like, like, like);
    }
    if (estado) {
        sql += " AND estado = ?";
        countSql += " AND estado = ?";
        params.push(estado);
        countParams.push(estado);
    }
    if (desde) {
        sql += " AND fecha_evaluacion >= ?";
        countSql += " AND fecha_evaluacion >= ?";
        params.push(desde);
        countParams.push(desde);
    }
    if (hasta) {
        sql += " AND fecha_evaluacion <= ?";
        countSql += " AND fecha_evaluacion <= ?";
        params.push(hasta + " 23:59:59");
        countParams.push(hasta + " 23:59:59");
    }

    sql += " ORDER BY id DESC LIMIT ? OFFSET ?";
    params.push(parseInt(limit), offset);

    db.query(countSql, countParams, (err, countResult) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta" });

        db.query(sql, params, (err, results) => {
            if (err) return res.status(500).json({ mensaje: "Error de consulta" });
            res.json({
                data: results,
                total: countResult[0].total,
                page: parseInt(page),
                totalPages: Math.ceil(countResult[0].total / parseInt(limit))
            });
        });
    });
});

router.get("/dashboard", (req, res) => {
    const sql = `
        SELECT 
            COUNT(*) AS total_evaluaciones,
            SUM(CASE WHEN estado = 'APROBADO' THEN 1 ELSE 0 END) AS aprobados,
            SUM(CASE WHEN estado LIKE 'REQUIERE%' THEN 1 ELSE 0 END) AS requiere_atencion,
            SUM(CASE WHEN estado = 'RECHAZADO' THEN 1 ELSE 0 END) AS rechazados,
            ROUND(AVG(score), 1) AS score_promedio,
            (SELECT COUNT(*) FROM evaluaciones_crediticias WHERE fecha_evaluacion >= CURDATE()) AS evaluaciones_hoy
        FROM evaluaciones_crediticias
    `;

    db.query(sql, (err, stats) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta" });

        db.query(
            "SELECT id, dni, cliente, score, clasificacion, estado, analista, fecha_evaluacion FROM evaluaciones_crediticias ORDER BY id DESC LIMIT 10",
            (err, recientes) => {
                if (err) return res.status(500).json({ mensaje: "Error de consulta" });
                res.json({ stats: stats[0], recientes });
            }
        );
    });
});

router.get("/:id", (req, res) => {
    db.query("SELECT * FROM evaluaciones_crediticias WHERE id = ?", [req.params.id], (err, results) => {
        if (err) return res.status(500).json({ mensaje: "Error de consulta" });
        if (results.length === 0) return res.status(404).json({ mensaje: "Evaluación no encontrada" });
        res.json(results[0]);
    });
});

module.exports = router;
