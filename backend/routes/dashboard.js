const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);

router.get("/", async (req, res) => {
    try {
        const [totalDesembolsado] = await query("SELECT COALESCE(SUM(monto),0) AS total FROM creditos");
        const [totalRecaudado] = await query("SELECT COALESCE(SUM(monto_pagado),0) AS total FROM pagos");
        const [totalClientes] = await query("SELECT COUNT(*) AS total FROM clientes");
        const [clientesHoy] = await query("SELECT COUNT(*) AS total FROM clientes WHERE DATE(fecha_registro) = CURDATE()");
        const [pendientes] = await query("SELECT COUNT(*) AS total FROM cronograma_pagos WHERE estado = 'Pendiente'");
        const [pagadas] = await query("SELECT COUNT(*) AS total FROM cronograma_pagos WHERE estado = 'Pagado'");
        const [activos] = await query("SELECT COUNT(*) AS total FROM creditos WHERE estado = 'Activo'");
        const proximosPagos = await query(`
            SELECT cp.id, cp.numero_cuota, cp.fecha_vencimiento, cp.monto_cuota,
                   c.nombre, c.dni, cr.monto AS credito_monto
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cp.estado = 'Pendiente'
              AND cp.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            ORDER BY cp.fecha_vencimiento ASC
            LIMIT 10
        `);
        const [morososCount] = await query(`
            SELECT COUNT(DISTINCT cr.cliente_id) AS total
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            WHERE cp.estado = 'Pendiente' AND cp.fecha_vencimiento < CURDATE()
        `);
        const pagosRecientes = await query(`
            SELECT p.id, p.fecha_pago, p.monto_pagado, p.metodo_pago,
                   cp.numero_cuota, c.nombre, c.dni
            FROM pagos p
            INNER JOIN cronograma_pagos cp ON p.cronograma_id = cp.id
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            ORDER BY p.fecha_pago DESC, p.id DESC
            LIMIT 5
        `);
        const deudores = await query(`
            SELECT cp.id, cp.numero_cuota, cp.fecha_vencimiento, cp.monto_cuota,
                   c.nombre, c.dni, c.telefono,
                   DATEDIFF(CURDATE(), cp.fecha_vencimiento) AS dias_vencido
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cp.estado = 'Pendiente' AND cp.fecha_vencimiento < CURDATE()
            ORDER BY cp.fecha_vencimiento ASC
            LIMIT 15
        `);
        res.json({
            total_clientes: totalClientes.total,
            total_desembolsado: parseFloat(totalDesembolsado.total).toFixed(2),
            total_recaudado: parseFloat(totalRecaudado.total).toFixed(2),
            clientes_hoy: clientesHoy.total,
            pendientes: pendientes.total,
            pagadas: pagadas.total,
            creditos_activos: activos.total,
            morosos: morososCount.total,
            proximos_pagos: proximosPagos,
            pagos_recientes: pagosRecientes,
            deudores: deudores
        });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;
