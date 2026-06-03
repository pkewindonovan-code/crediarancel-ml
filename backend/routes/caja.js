const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);

router.get("/diario", async (req, res) => {
    try {
        const [cobros] = await query(`
            SELECT COALESCE(SUM(p.monto_pagado),0) AS total, COUNT(*) AS cantidad
            FROM pagos p WHERE DATE(p.fecha_pago) = CURDATE()
        `);
        const [desembolsos] = await query(`
            SELECT COALESCE(SUM(monto),0) AS total, COUNT(*) AS cantidad
            FROM creditos WHERE DATE(fecha_inicio) = CURDATE()
        `);
        const cobrosDetalle = await query(`
            SELECT p.id, p.monto_pagado, p.metodo_pago, p.fecha_pago,
                   cp.numero_cuota, c.nombre, c.dni
            FROM pagos p
            INNER JOIN cronograma_pagos cp ON p.cronograma_id = cp.id
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE DATE(p.fecha_pago) = CURDATE()
            ORDER BY p.fecha_pago DESC
        `);
        const desembolsosDetalle = await query(`
            SELECT cr.id, cr.monto, cr.cuotas, cr.frecuencia_pago, cr.fecha_inicio,
                   c.nombre, c.dni
            FROM creditos cr
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE DATE(cr.fecha_inicio) = CURDATE()
            ORDER BY cr.fecha_inicio DESC
        `);
        res.json({
            cobros: { total: parseFloat(cobros.total).toFixed(2), cantidad: cobros.cantidad, detalle: cobrosDetalle },
            desembolsos: { total: parseFloat(desembolsos.total).toFixed(2), cantidad: desembolsos.cantidad, detalle: desembolsosDetalle }
        });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;
