const express = require("express");
const router = express.Router();
const db = require("../db");

// LISTAR CLIENTES CON RESUMEN
router.get("/", (req, res) => {
    const sql = `
        SELECT 
            c.id,
            c.dni,
            c.nombre,
            c.telefono,
            c.direccion,

            COUNT(DISTINCT cr.id) AS total_creditos,

            SUM(CASE WHEN cp.estado = 'Pendiente' THEN 1 ELSE 0 END) AS cuotas_pendientes,
            SUM(CASE WHEN cp.estado = 'Pagado' THEN 1 ELSE 0 END) AS cuotas_pagadas,

            SUM(CASE WHEN cp.estado = 'Pendiente' THEN cp.monto_cuota ELSE 0 END) AS deuda_pendiente,

            CASE 
                WHEN COUNT(DISTINCT cr.id) > 0 THEN 'Sí'
                ELSE 'No'
            END AS tiene_credito

        FROM clientes c
        LEFT JOIN creditos cr ON c.id = cr.cliente_id
        LEFT JOIN cronograma_pagos cp ON cr.id = cp.credito_id
        GROUP BY c.id
        ORDER BY c.id DESC
    `;

    db.query(sql, (err, results) => {
        if (err) return res.status(500).json(err);
        res.json(results);
    });
});

// BUSCAR POR DNI
router.get("/dni/:dni", (req, res) => {
    const dni = req.params.dni;

    db.query(
        "SELECT * FROM clientes WHERE dni = ?",
        [dni],
        (err, results) => {
            if (err) return res.status(500).json(err);
            res.json(results);
        }
    );
});

// REGISTRAR
router.post("/", (req, res) => {
    const { dni, nombre, telefono, direccion } = req.body;

    db.query(
        "INSERT INTO clientes(dni,nombre,telefono,direccion) VALUES(?,?,?,?)",
        [dni, nombre, telefono, direccion],
        (err) => {
            if (err) return res.status(500).json({ mensaje: "Error al registrar cliente" });

            res.json({
                mensaje: "Cliente registrado correctamente"
            });
        }
    );
});

// ACTUALIZAR
router.put("/:id", (req, res) => {
    const id = req.params.id;
    const { dni, nombre, telefono, direccion } = req.body;

    db.query(
        "UPDATE clientes SET dni=?, nombre=?, telefono=?, direccion=? WHERE id=?",
        [dni, nombre, telefono, direccion, id],
        (err) => {
            if (err) return res.status(500).json({ mensaje: "Error al actualizar cliente" });

            res.json({
                mensaje: "Cliente actualizado correctamente"
            });
        }
    );
});

// ELIMINAR (en cadena: vouchers → pagos → cronograma → creditos → cliente)
router.delete("/:id", (req, res) => {
    const id = req.params.id;

    function eliminarCreditos(credIds, cb) {
        const ph = credIds.map(() => "?").join(",");
        db.query(`DELETE FROM creditos WHERE id IN (${ph})`, credIds, (err) => {
            if (err) return cb(err);
            db.query("DELETE FROM clientes WHERE id=?", [id], (err2) => {
                if (err2) return cb(err2);
                cb(null);
            });
        });
    }

    db.query("SELECT id FROM creditos WHERE cliente_id=?", [id], (err, creditos) => {
        if (err) return res.status(500).json({ mensaje: "Error al eliminar cliente" });

        const ids = creditos.map(c => c.id);
        if (ids.length === 0) {
            db.query("DELETE FROM clientes WHERE id=?", [id], (err2) => {
                if (err2) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                res.json({ mensaje: "Cliente eliminado correctamente" });
            });
            return;
        }

        const ph = ids.map(() => "?").join(",");
        db.query(`SELECT id FROM cronograma_pagos WHERE credito_id IN (${ph})`, ids, (err3, cronoRows) => {
            if (err3) return res.status(500).json({ mensaje: "Error al eliminar cliente" });

            const cronoIds = cronoRows.map(r => r.id);
            if (cronoIds.length === 0) {
                eliminarCreditos(ids, (err) => {
                    if (err) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                    res.json({ mensaje: "Cliente y créditos eliminados correctamente" });
                });
                return;
            }

            const cp = cronoIds.map(() => "?").join(",");
            db.query(`DELETE FROM vouchers WHERE pago_id IN (SELECT id FROM pagos WHERE cronograma_id IN (${cp}))`, cronoIds, (err4) => {
                if (err4) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                db.query(`DELETE FROM pagos WHERE cronograma_id IN (${cp})`, cronoIds, (err5) => {
                    if (err5) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                    db.query(`DELETE FROM cronograma_pagos WHERE id IN (${cp})`, cronoIds, (err6) => {
                        if (err6) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                        eliminarCreditos(ids, (err7) => {
                            if (err7) return res.status(500).json({ mensaje: "Error al eliminar cliente" });
                            res.json({ mensaje: "Cliente y sus créditos eliminados correctamente" });
                        });
                    });
                });
            });
        });
    });
});

// PERFIL COMPLETO DEL CLIENTE
const { promisify } = require("util");
router.get("/:id/perfil", async (req, res) => {
    try {
        const id = req.params.id;
        const q = promisify(db.query).bind(db);
        const clientes = await q("SELECT * FROM clientes WHERE id = ?", [id]);
        if (clientes.length === 0) return res.status(404).json({ mensaje: "Cliente no encontrado" });
        const cliente = clientes[0];
        let creditos, pagos;
        try {
            creditos = await q(`
                SELECT cr.id, cr.monto, cr.interes, cr.cuotas, cr.frecuencia_pago,
                       cr.fecha_inicio, cr.estado, COALESCE(cr.estado_cobranza,'Normal') AS estado_cobranza,
                       (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id AND cp.estado = 'Pagado') AS cuotas_pagadas,
                       (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id) AS total_cuotas,
                       (SELECT COALESCE(SUM(cp.monto_cuota),0) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id AND cp.estado = 'Pendiente') AS saldo_pendiente
                FROM creditos cr WHERE cr.cliente_id = ? ORDER BY cr.id DESC
            `, [id]);
        } catch (e) {
            creditos = await q(`
                SELECT cr.id, cr.monto, cr.interes, cr.cuotas, cr.frecuencia_pago,
                       cr.fecha_inicio, cr.estado, 'Normal' AS estado_cobranza,
                       (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id AND cp.estado = 'Pagado') AS cuotas_pagadas,
                       (SELECT COUNT(*) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id) AS total_cuotas,
                       (SELECT COALESCE(SUM(cp.monto_cuota),0) FROM cronograma_pagos cp WHERE cp.credito_id = cr.id AND cp.estado = 'Pendiente') AS saldo_pendiente
                FROM creditos cr WHERE cr.cliente_id = ? ORDER BY cr.id DESC
            `, [id]);
        }
        pagos = await q(`
            SELECT p.fecha_pago, p.monto_pagado, p.metodo_pago, cp.numero_cuota
            FROM pagos p INNER JOIN cronograma_pagos cp ON p.cronograma_id = cp.id
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            WHERE cr.cliente_id = ? ORDER BY p.fecha_pago DESC LIMIT 20
        `, [id]);
        res.json({ cliente, creditos, pagos });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;