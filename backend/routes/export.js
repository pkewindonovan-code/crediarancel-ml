const express = require("express");
const router = express.Router();
const db = require("../db");
const ExcelJS = require("exceljs");
const path = require("path");
const fs = require("fs");
const { promisify } = require("util");
const query = promisify(db.query).bind(db);

const HEADER_BG = "EFB183";
const TABLE_BG = "F39C12";
const thin = { style: "thin", color: { argb: "FF000000" } };
const border = { top: thin, bottom: thin, left: thin, right: thin };
const FONT = { name: "Arial", color: { argb: "FF000000" } };

function fmtFecha(f) {
    if (!f) return "-";
    const d = new Date(f);
    return String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0") + "/" + d.getFullYear();
}

function setCell(ws, r, c, val, fontOpt, align, fillColor) {
    const cl = ws.getCell(r, c);
    cl.value = val;
    cl.font = { ...FONT, ...(fontOpt || {}) };
    if (align) cl.alignment = align;
    if (fillColor) cl.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + fillColor } };
    cl.border = border;
}

function buildBlock(ws, offset, data, total) {
    const o = offset;
    const c = data[0];

    // ── Rows 1-3: Header ──
    ws.getRow(1).height = 20;
    ws.getRow(2).height = 18;
    ws.getRow(3).height = 18;
    ws.mergeCells(1, 1 + o, 3, 1 + o);
    for (let r = 1; r <= 3; r++) {
        for (let cc = 2 + o; cc <= 6 + o; cc++) {
            ws.getCell(r, cc).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + HEADER_BG } };
            ws.getCell(r, cc).border = border;
        }
    }
    for (let r = 1; r <= 3; r++) {
        ws.getCell(r, 1 + o).border = border;
        ws.getCell(r, 1 + o).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + HEADER_BG } };
    }

    ws.mergeCells(1, 2 + o, 1, 6 + o);
    setCell(ws, 1, 2 + o, "FINANCIERA ARANCEL", { bold: true, size: 12 }, { horizontal: "center", vertical: "middle" }, HEADER_BG);

    ws.mergeCells(2, 2 + o, 2, 6 + o);
    setCell(ws, 2, 2 + o, '"Empodera Tu Éxito"', { bold: true, size: 9, italic: true }, { horizontal: "center", vertical: "middle" }, HEADER_BG);

    ws.mergeCells(3, 2 + o, 3, 6 + o);
    setCell(ws, 3, 2 + o, "CRONOGRAMA DE PAGO", { bold: true, size: 11 }, { horizontal: "center", vertical: "middle" }, HEADER_BG);

    // ── Rows 4-7: Client data ──
    for (let r = 4; r <= 7; r++) {
        ws.getRow(r).height = 16;
        for (let cc = 1 + o; cc <= 6 + o; cc++) {
            ws.getCell(r, cc).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + HEADER_BG } };
            ws.getCell(r, cc).border = border;
        }
    }

    ws.mergeCells(4, 1 + o, 4, 6 + o);
    setCell(ws, 4, 1 + o, "Cliente: " + c.nombre, { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);

    ws.mergeCells(5, 1 + o, 5, 4 + o);
    setCell(ws, 5, 1 + o, "Dirección: " + (c.direccion || "-"), { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);
    ws.mergeCells(5, 5 + o, 5, 6 + o);
    setCell(ws, 5, 5 + o, "Monto: S/ " + parseFloat(c.monto).toFixed(2), { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);

    ws.mergeCells(6, 1 + o, 6, 4 + o);
    setCell(ws, 6, 1 + o, "Fecha desemb: " + (c.fecha_inicio ? fmtFecha(c.fecha_inicio) : "-"), { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);
    ws.mergeCells(6, 5 + o, 6, 6 + o);
    setCell(ws, 6, 5 + o, "Cuota: S/ " + parseFloat(c.monto_cuota || 0).toFixed(2), { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);

    ws.mergeCells(7, 1 + o, 7, 4 + o);
    setCell(ws, 7, 1 + o, "Celular: " + (c.telefono || "-"), { bold: true, size: 9 }, { vertical: "middle" }, HEADER_BG);
    ws.mergeCells(7, 5 + o, 7, 6 + o);
    setCell(ws, 7, 5 + o, "", null, null, HEADER_BG);

    // ── Row 8: Table header ──
    ws.getRow(8).height = 17;
    const headers = ["N°", "Fech. Prog.", "Fecha de pago", "Cuota", "Saldo", "Firma"];
    headers.forEach((h, i) => {
        setCell(ws, 8, i + 1 + o, h, { bold: true, size: 9 }, { horizontal: "center", vertical: "middle" }, TABLE_BG);
    });

    // ── Row 9: Total a pagar ──
    ws.getRow(9).height = 15;
    const totalStr = "S/ " + total.toFixed(2);
    const totalRowData = ["Total", "", "", "", totalStr, ""];
    totalRowData.forEach((v, i) => {
        setCell(ws, 9, i + 1 + o, v, { bold: true, size: 8 }, { horizontal: i === 0 || i === 5 ? "center" : i >= 3 ? "right" : "center", vertical: "middle" });
    });

    // ── Rows 10+: Cuota data ──
    let saldo = total;
    data.forEach((cuota, idx) => {
        const r = 10 + idx;
        ws.getRow(r).height = 15;
        saldo -= parseFloat(cuota.monto_cuota);
        const vals = [
            String(cuota.numero_cuota),
            fmtFecha(cuota.fecha_vencimiento),
            cuota.estado === "Pagado" ? fmtFecha(cuota.fecha_vencimiento) : "",
            "S/ " + parseFloat(cuota.monto_cuota).toFixed(2),
            "S/ " + Math.max(0, saldo).toFixed(2),
            ""
        ];
        vals.forEach((v, i) => {
            const isBold = i === 0 || i === 3;
            setCell(ws, r, i + 1 + o, v, { bold: isBold, size: 8 }, { horizontal: i === 0 || i === 5 ? "center" : i >= 3 ? "right" : "center", vertical: "middle" });
        });
    });
    // 5px gap after last data row
    if (data.length > 0) ws.getRow(9 + data.length).height = 20;

    // ── Footer ──
    const lastDataRow = 9 + data.length;
    const noteRow = lastDataRow + 1;
    ws.getRow(noteRow).height = 13;
    ws.mergeCells(noteRow, 1 + o, noteRow, 6 + o);
    setCell(ws, noteRow, 1 + o, "NOTA: por cada día de retraso el cliente abonará S/ 2.00 soles.", { size: 7, italic: true }, { horizontal: "center", vertical: "middle" }, HEADER_BG);

    const msgRow = noteRow + 1;
    ws.getRow(msgRow).height = 13;
    ws.mergeCells(msgRow, 1 + o, msgRow, 6 + o);
    setCell(ws, msgRow, 1 + o, "RECUERDE QUE EL ÉXITO SIEMPRE SERÁ TUYO......", { bold: true, italic: true, size: 7 }, { horizontal: "center", vertical: "middle" }, HEADER_BG);

    const asesorRow = msgRow + 1;
    ws.getRow(asesorRow).height = 20;
    ws.mergeCells(asesorRow, 1 + o, asesorRow, 6 + o);
    setCell(ws, asesorRow, 1 + o, "AS. ARANCEL TOTOS LIMBER\nCEL: 947066810", { size: 7 }, { horizontal: "center", vertical: "middle", wrapText: true }, HEADER_BG);

    // ── Row 42: Signature + YAPEA + QR ──
    const sigRow = asesorRow + 1;
    ws.getRow(sigRow).height = 72;
    ws.mergeCells(sigRow, 1 + o, sigRow, 4 + o);
    setCell(ws, sigRow, 1 + o, o === 0 ? "____________________________\nFirma del Analista" : "____________________________\nFirma del Cliente", { size: 9 }, { horizontal: "center", vertical: "middle", wrapText: true }, HEADER_BG);
    ws.mergeCells(sigRow, 5 + o, sigRow, 6 + o);
    setCell(ws, sigRow, 5 + o, "YAPEA\n947066810", { bold: true, size: 7 }, { horizontal: "center", vertical: "top", wrapText: true }, HEADER_BG);
}

router.post("/cronograma", async (req, res) => {
    try {
        const { creditoId } = req.body;
        if (!creditoId) return res.status(400).json({ error: "creditoId requerido" });

        const sql = `SELECT cp.id, cp.numero_cuota, cp.fecha_vencimiento, cp.monto_cuota, cp.estado, c.nombre, c.direccion, c.telefono, c.dni, cr.id AS credito_id, cr.monto, cr.interes, cr.cuotas, cr.frecuencia_pago, cr.fecha_inicio FROM cronograma_pagos cp INNER JOIN creditos cr ON cp.credito_id = cr.id INNER JOIN clientes c ON cr.cliente_id = c.id WHERE cr.id = ? ORDER BY cp.numero_cuota ASC`;
        const resultados = await query(sql, [creditoId]);
        if (resultados.length === 0) return res.status(404).json({ error: "No data" });

        const c = resultados[0];
        const total = parseFloat(c.monto) + (parseFloat(c.monto) * parseFloat(c.interes) / 100);

        const wb = new ExcelJS.Workbook();
        // Load QR image from file (two separate IDs to avoid ExcelJS rId reuse bug)
        const qrPath = path.join(__dirname, "..", "..", "frontend", "qr.png");
        const qrBuf = fs.readFileSync(qrPath);
        const qrImgId1 = wb.addImage({ buffer: qrBuf, extension: "png" });
        const qrImgId2 = wb.addImage({ buffer: qrBuf, extension: "png" });

        let logoImgId = null, logoImgId2 = null;
        const logoPath = path.join(__dirname, "..", "..", "frontend", "logo.png");
        if (fs.existsSync(logoPath)) {
            const logoBuf = fs.readFileSync(logoPath);
            logoImgId = wb.addImage({ buffer: logoBuf, extension: "png" });
            logoImgId2 = wb.addImage({ buffer: logoBuf, extension: "png" });
        }

        const ws = wb.addWorksheet("Cronograma");

        // Page setup — A4 landscape, fit to 1 page, tight margins
        ws.pageSetup = {
            paperSize: 9,
            orientation: "landscape",
            fitToPage: true,
            fitToWidth: 1,
            fitToHeight: 1,
            scale: 80,
            margins: { left: 0.10, right: 0.10, top: 0.10, bottom: 0.10, header: 0, footer: 0 }
        };

        // Print area: dynamic based on number of cuotas (+1 for total row)
        const qrRow1Idx = 13 + resultados.length; // sigRow (1-indexed)
        ws.pageSetup.printArea = "A1:M" + qrRow1Idx;

        // Column widths (use string '9' to avoid ExcelJS bug with integer 9)
        const colWidths = [3.5, '9', '9', 7, 7, '9', 2, 3.5, '9', '9', 7, 7, '9'];
        for (let i = 0; i < colWidths.length; i++) {
            ws.getColumn(i + 1).width = colWidths[i];
        }

        // Build both blocks
        buildBlock(ws, 0, resultados, total);
        buildBlock(ws, 7, resultados, total);

        // Add logo to both blocks (separate image IDs)
        if (logoImgId !== null) {
            ws.addImage(logoImgId, { tl: { col: 0, row: 0 }, ext: { width: 55, height: 55 } });
            ws.addImage(logoImgId2, { tl: { col: 7, row: 0 }, ext: { width: 55, height: 55 } });
        }

        // Add QR below YAPEA (dynamic row, centered in E-F/L-M merge)
        const qrRow0Idx = qrRow1Idx - 1; // 0-indexed row for image placement
        ws.addImage(qrImgId1, { tl: { col: 4.5, row: qrRow0Idx, rowOff: 238125 }, ext: { width: 45, height: 45 } });
        ws.addImage(qrImgId2, { tl: { col: 11.5, row: qrRow0Idx, rowOff: 238125 }, ext: { width: 45, height: 45 } });

        res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        res.setHeader("Content-Disposition", "attachment; filename=cronograma_" + c.dni + "_" + c.credito_id + ".xlsx");
        await wb.xlsx.write(res);
        res.end();
    } catch (error) {
        console.error("Export error:", error);
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
