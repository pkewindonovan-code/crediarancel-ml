const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);

// BUSCAR CUOTAS PENDIENTES POR DNI
router.get("/dni/:dni", async (req, res) => {
    try {
        const { dni } = req.params;

        const cuotas = await query(`
            SELECT 
                cp.id,
                cp.credito_id,
                cp.numero_cuota,
                cp.fecha_vencimiento,
                cp.monto_cuota,
                cp.estado,
                c.nombre,
                c.dni,
                c.telefono,
                c.direccion,
                cr.monto AS credito_monto,
                cr.interes,
                cr.frecuencia_pago,
                (SELECT COUNT(*) FROM cronograma_pagos cp2 WHERE cp2.credito_id = cr.id AND cp2.estado = 'Pagado') AS cuotas_pagadas,
                (SELECT COUNT(*) FROM cronograma_pagos cp2 WHERE cp2.credito_id = cr.id) AS total_cuotas
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE c.dni = ?
            AND cp.estado = 'Pendiente'
            ORDER BY cr.id DESC, cp.numero_cuota ASC
        `, [dni]);

        if (cuotas.length === 0) {
            return res.status(404).json({ mensaje: "No hay cuotas pendientes para este DNI" });
        }

        res.json(cuotas);
    } catch (error) {
        console.error("Error al buscar cuotas:", error);
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// REGISTRAR PAGO
router.post("/", async (req, res) => {
    try {
        const { cronograma_id, monto_pagado, metodo_pago } = req.body;

        if (!cronograma_id || !monto_pagado || !metodo_pago) {
            return res.status(400).json({ mensaje: "Faltan datos requeridos" });
        }

        const cuotas = await query(
            "SELECT cp.*, c.nombre, c.dni, c.telefono, c.direccion, cr.monto AS credito_monto, cr.interes, cr.frecuencia_pago FROM cronograma_pagos cp INNER JOIN creditos cr ON cp.credito_id = cr.id INNER JOIN clientes c ON cr.cliente_id = c.id WHERE cp.id = ?",
            [cronograma_id]
        );

        if (cuotas.length === 0) {
            return res.status(404).json({ mensaje: "Cuota no encontrada" });
        }

        if (cuotas[0].estado === "Pagado") {
            return res.status(400).json({ mensaje: "Esta cuota ya fue pagada" });
        }

        const cuota = cuotas[0];
        const fecha_pago = new Date().toISOString().split("T")[0];

        const resultado = await query(
            "INSERT INTO pagos (cronograma_id, fecha_pago, monto_pagado, metodo_pago) VALUES (?, ?, ?, ?)",
            [cronograma_id, fecha_pago, monto_pagado, metodo_pago]
        );

        const pago_id = resultado.insertId;
        const codigo_voucher = "VCH-" + String(pago_id).padStart(5, "0");

        await query("UPDATE cronograma_pagos SET estado = 'Pagado' WHERE id = ?", [cronograma_id]);
        await query("INSERT INTO vouchers (pago_id, codigo_voucher) VALUES (?, ?)", [pago_id, codigo_voucher]);

        res.json({
            mensaje: "Pago registrado correctamente",
            pago_id,
            codigo_voucher,
            cuota: {
                id: cuota.id,
                credito_id: cuota.credito_id,
                numero_cuota: cuota.numero_cuota,
                fecha_vencimiento: cuota.fecha_vencimiento,
                monto_cuota: cuota.monto_cuota,
                credito_monto: cuota.credito_monto,
                interes: cuota.interes,
                frecuencia_pago: cuota.frecuencia_pago,
                nombre: cuota.nombre,
                dni: cuota.dni,
                telefono: cuota.telefono,
                direccion: cuota.direccion
            },
            fecha_pago,
            metodo_pago,
            monto_pagado
        });
    } catch (error) {
        console.error("Error al registrar pago:", error);
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

// RESUMEN DE PAGOS
router.get("/resumen", async (req, res) => {
    try {
        const [pendientes] = await query("SELECT COUNT(*) AS total FROM cronograma_pagos WHERE estado = 'Pendiente'");
        const [pagadas] = await query("SELECT COUNT(*) AS total FROM cronograma_pagos WHERE estado = 'Pagado'");
        const [totalRecaudado] = await query("SELECT COALESCE(SUM(monto_pagado),0) AS total FROM pagos");
        const [totalDesembolsado] = await query("SELECT COALESCE(SUM(monto),0) AS total FROM creditos");
        res.json({
            pendientes: pendientes.total,
            pagadas: pagadas.total,
            total_recaudado: parseFloat(totalRecaudado.total).toFixed(2),
            total_desembolsado: parseFloat(totalDesembolsado.total).toFixed(2)
        });
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;
