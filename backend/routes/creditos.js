const express = require("express");
const router = express.Router();
const db = require("../db");
const { promisify } = require("util");
const query = promisify(db.query).bind(db);

// FERIADOS PERÚ 2026
const FERIADOS_PERU = [
    "2026-01-01",
    "2026-04-02",
    "2026-04-03",
    "2026-05-01",
    "2026-06-07",
    "2026-06-29",
    "2026-07-23",
    "2026-07-28",
    "2026-07-29",
    "2026-08-06",
    "2026-08-30",
    "2026-10-08",
    "2026-11-01",
    "2026-12-08",
    "2026-12-09",
    "2026-12-25"

];

function esDiaHabil(fecha) {
    const dia = fecha.getDay();
    if (dia === 0) return false;
    const str = fecha.toLocaleDateString("en-CA", { timeZone: "America/Lima" });
    return !FERIADOS_PERU.includes(str);
}

function siguienteDiaHabil(fecha) {
    const f = new Date(fecha);
    f.setDate(f.getDate() + 1);
    while (!esDiaHabil(f)) {
        f.setDate(f.getDate() + 1);
    }
    return f;
}

// REGISTRAR CRÉDITO Y GENERAR CRONOGRAMA
router.post("/", async (req, res) => {
    try {
        const {
            cliente_id,
            monto,
            interes,
            cuotas,
            frecuencia_pago,
            fecha_inicio
        } = req.body;

        if (!cliente_id) {
            return res.status(400).json({ mensaje: "Debe seleccionar un cliente" });
        }

        // Verificar que el cliente existe
        const clientes = await query(
            "SELECT id, nombre, dni, telefono, direccion FROM clientes WHERE id = ?",
            [cliente_id]
        );

        if (clientes.length === 0) {
            return res.status(404).json({ mensaje: "Cliente no encontrado" });
        }

        const cliente = clientes[0];
        const estado = "Activo";

        const resultado = await query(
            `INSERT INTO creditos
            (cliente_id, monto, interes, cuotas, frecuencia_pago, fecha_inicio, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?)`,
            [cliente_id, monto, interes, cuotas, frecuencia_pago, fecha_inicio, estado]
        );

        const credito_id = resultado.insertId;
        const total = parseFloat(monto) + (parseFloat(monto) * parseFloat(interes) / 100);
        const montoCuota = (total / parseInt(cuotas)).toFixed(2);
        const fechasGeneradas = [];

        // Generar cronograma evitando duplicados, domingos y feriados Perú
        const fechasUsadas = new Set();
        for (let i = 1; i <= parseInt(cuotas); i++) {
            let fecha = new Date(fecha_inicio + "T00:00:00-05:00");

            if (frecuencia_pago === "Diario") {
                fecha.setDate(fecha.getDate() + i);
            } else if (frecuencia_pago === "Semanal") {
                fecha.setDate(fecha.getDate() + (i * 7));
            } else if (frecuencia_pago === "Quincenal") {
                fecha.setDate(fecha.getDate() + (i * 15));
            } else {
                fecha.setMonth(fecha.getMonth() + i);
            }

            // Saltar domingos y feriados
            while (!esDiaHabil(fecha)) {
                fecha.setDate(fecha.getDate() + 1);
            }

            // Evitar fechas duplicadas por colisión
            let fechaStr = fecha.toLocaleDateString("en-CA", { timeZone: "America/Lima" });
            while (fechasUsadas.has(fechaStr)) {
                fecha.setDate(fecha.getDate() + 1);
                while (!esDiaHabil(fecha)) {
                    fecha.setDate(fecha.getDate() + 1);
                }
                fechaStr = fecha.toLocaleDateString("en-CA", { timeZone: "America/Lima" });
            }
            fechasUsadas.add(fechaStr);
            fechasGeneradas.push(fechaStr);

            await query(
                `INSERT INTO cronograma_pagos
                (credito_id, numero_cuota, fecha_vencimiento, monto_cuota, estado)
                VALUES (?, ?, ?, ?, ?)`,
                [credito_id, i, fechaStr, montoCuota, "Pendiente"]
            );
        }

        res.json({
            mensaje: "Crédito y cronograma registrados correctamente",
            credito_id,
            total: total.toFixed(2),
            monto_cuota: montoCuota,
            fechas: fechasGeneradas,
            cliente: {
                nombre: cliente.nombre,
                dni: cliente.dni,
                telefono: cliente.telefono,
                direccion: cliente.direccion
            }
        });

    } catch (error) {
        console.error("Error al registrar crédito:", error);
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// LISTAR TODOS LOS CRÉDITOS
router.get("/", async (req, res) => {
    try {
        let creditos;
        try {
            creditos = await query("SELECT id, monto, interes, cuotas, frecuencia_pago, fecha_inicio, estado, COALESCE(estado_cobranza,'Normal') AS estado_cobranza FROM creditos ORDER BY id DESC");
        } catch (e) {
            creditos = await query("SELECT id, monto, interes, cuotas, frecuencia_pago, fecha_inicio, estado, 'Normal' AS estado_cobranza FROM creditos ORDER BY id DESC");
        }
        res.json(creditos);
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// LISTAR TODOS LOS CRÉDITOS DE UN CLIENTE POR DNI
router.get("/dni/:dni", async (req, res) => {
    try {
        const { dni } = req.params;
        const creditos = await query(`
            SELECT cr.id, cr.monto, cr.interes, cr.cuotas, cr.frecuencia_pago,
                   cr.fecha_inicio, cr.estado,
                   (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id AND cp.estado = 'Pagado') AS cuotas_pagadas,
                   (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id) AS total_cuotas
            FROM creditos cr
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE c.dni = ?
            ORDER BY cr.id DESC
        `, [dni]);

        if (creditos.length === 0) {
            return res.status(404).json({ mensaje: "No se encontraron créditos para este DNI" });
        }

        res.json(creditos);
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// VER CRONOGRAMA POR ID DE CRÉDITO
router.get("/:id/cronograma", async (req, res) => {
    try {
        const { id } = req.params;

        const sql = `
            SELECT 
                cp.id, cp.numero_cuota, cp.fecha_vencimiento, cp.monto_cuota,
                cp.estado,
                c.nombre, c.direccion, c.telefono, c.dni,
                cr.id AS credito_id, cr.monto, cr.interes, cr.cuotas,
                cr.frecuencia_pago, cr.fecha_inicio
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cr.id = ?
            ORDER BY cp.numero_cuota ASC
        `;

        const resultados = await query(sql, [id]);

        if (resultados.length === 0) {
            return res.status(404).json({ mensaje: "Cronograma no encontrado" });
        }

        res.json(resultados);
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// VER CRONOGRAMA POR DNI (último crédito - compatibilidad)
router.get("/dni/:dni/cronograma", async (req, res) => {
    try {
        const { dni } = req.params;

        const creditos = await query(
            "SELECT id FROM creditos WHERE id = (SELECT MAX(cr2.id) FROM creditos cr2 INNER JOIN clientes c2 ON cr2.cliente_id = c2.id WHERE c2.dni = ?)",
            [dni]
        );

        if (creditos.length === 0) {
            return res.status(404).json({ mensaje: "No hay créditos para este DNI" });
        }

        // Redirigir al nuevo endpoint
        const { id } = creditos[0];
        const resultados = await query(`
            SELECT 
                cp.id, cp.numero_cuota, cp.fecha_vencimiento, cp.monto_cuota,
                cp.estado,
                c.nombre, c.direccion, c.telefono, c.dni,
                cr.id AS credito_id, cr.monto, cr.interes, cr.cuotas,
                cr.frecuencia_pago, cr.fecha_inicio
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cr.id = ?
            ORDER BY cp.numero_cuota ASC
        `, [id]);

        res.json(resultados);
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// ACTUALIZAR ESTADO DE COBRANZA
router.put("/:id/cobranza", async (req, res) => {
    try {
        const { id } = req.params;
        const { estado_cobranza } = req.body;
        const validos = ["Normal", "Contactado", "Prometió pago", "En cobranza judicial", "Incobrable"];
        if (!validos.includes(estado_cobranza)) {
            return res.status(400).json({ mensaje: "Estado de cobranza no válido" });
        }
        await query("UPDATE creditos SET estado_cobranza = ? WHERE id = ?", [estado_cobranza, id]);
        res.json({ mensaje: "Estado de cobranza actualizado" });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// REPROGRAMAR CUOTA (diferir)
router.put("/:id/reprogramar", async (req, res) => {
    try {
        const { id } = req.params;
        const { cronograma_id, nueva_fecha } = req.body;
        if (!cronograma_id || !nueva_fecha) {
            return res.status(400).json({ mensaje: "Faltan datos" });
        }
        const f = new Date(nueva_fecha + "T00:00:00-05:00");
        if (!esDiaHabil(f)) {
            return res.status(400).json({ mensaje: "La nueva fecha debe ser un día hábil (lun-sáb, no feriado)" });
        }
        await query("UPDATE cronograma_pagos SET fecha_vencimiento = ? WHERE id = ? AND credito_id = ?", [nueva_fecha, cronograma_id, id]);
        res.json({ mensaje: "Cuota reprogramada correctamente" });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;