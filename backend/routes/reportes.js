const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);
const ExcelJS = require("exceljs");

router.get("/mensual", async (req, res) => {
    try {
        const { mes, anio } = req.query;
        const m = parseInt(mes) || (new Date().getMonth() + 1);
        const a = parseInt(anio) || new Date().getFullYear();
        const inicio = `${a}-${String(m).padStart(2,"0")}-01`;
        const fin = `${a}-${String(m).padStart(2,"0")}-31`;

        const cobros = await query(`
            SELECT p.fecha_pago, p.monto_pagado, p.metodo_pago,
                   cp.numero_cuota, c.nombre, c.dni
            FROM pagos p
            INNER JOIN cronograma_pagos cp ON p.cronograma_id = cp.id
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE p.fecha_pago BETWEEN ? AND ?
            ORDER BY p.fecha_pago ASC
        `, [inicio, fin]);

        const desembolsos = await query(`
            SELECT cr.fecha_inicio, cr.monto, cr.cuotas, c.nombre, c.dni
            FROM creditos cr INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cr.fecha_inicio BETWEEN ? AND ?
            ORDER BY cr.fecha_inicio ASC
        `, [inicio, fin]);

        const morosos = await query(`
            SELECT c.nombre, c.dni, cp.fecha_vencimiento, cp.monto_cuota,
                   DATEDIFF(CURDATE(), cp.fecha_vencimiento) AS dias_vencido
            FROM cronograma_pagos cp
            INNER JOIN creditos cr ON cp.credito_id = cr.id
            INNER JOIN clientes c ON cr.cliente_id = c.id
            WHERE cp.estado = 'Pendiente' AND cp.fecha_vencimiento < CURDATE()
            ORDER BY dias_vencido DESC
        `);

        const wb = new ExcelJS.Workbook();
        const ws = wb.addWorksheet(`Reporte ${m}-${a}`);

        ws.addRow([`Reporte Mensual - ${String(m).padStart(2,"0")}/${a}`]);
        ws.addRow([`Generado: ${new Date().toLocaleDateString("es-PE")}`]);
        ws.addRow([]);

        ws.addRow(["COBROS DEL MES"]);
        ws.addRow(["Fecha", "Cliente", "DNI", "Cuota", "Método", "Monto"]);
        let totalCobros = 0;
        cobros.forEach(c => {
            ws.addRow([c.fecha_pago, c.nombre, c.dni, `N°${c.numero_cuota}`, c.metodo_pago, parseFloat(c.monto_pagado).toFixed(2)]);
            totalCobros += parseFloat(c.monto_pagado);
        });
        ws.addRow([]);
        ws.addRow(["Total Cobros", "", "", "", "", totalCobros.toFixed(2)]);

        ws.addRow([]);
        ws.addRow(["DESEMBOLSOS DEL MES"]);
        ws.addRow(["Fecha", "Cliente", "DNI", "Monto", "Cuotas"]);
        let totalDesem = 0;
        desembolsos.forEach(d => {
            ws.addRow([d.fecha_inicio, d.nombre, d.dni, parseFloat(d.monto).toFixed(2), d.cuotas]);
            totalDesem += parseFloat(d.monto);
        });
        ws.addRow([]);
        ws.addRow(["Total Desembolsos", "", "", totalDesem.toFixed(2), ""]);

        ws.addRow([]);
        ws.addRow(["DEUDORES MOROSOS"]);
        ws.addRow(["Cliente", "DNI", "Vencido desde", "Días", "Monto"]);
        morosos.forEach(m => {
            ws.addRow([m.nombre, m.dni, m.fecha_vencimiento, m.dias_vencido, parseFloat(m.monto_cuota).toFixed(2)]);
        });

        ws.getColumn(1).width = 14;
        ws.getColumn(2).width = 25;
        ws.getColumn(3).width = 12;
        ws.getColumn(4).width = 12;
        ws.getColumn(5).width = 14;
        ws.getColumn(6).width = 12;

        res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        res.setHeader("Content-Disposition", `attachment; filename=reporte_${a}_${String(m).padStart(2,"0")}.xlsx`);
        await wb.xlsx.write(res);
        res.end();
    } catch (error) {
        res.status(500).json({ mensaje: "Error del servidor", error: error.message });
    }
});

module.exports = router;
