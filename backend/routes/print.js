const express = require("express");
const router = express.Router();
const { execFile } = require("child_process");
const path = require("path");

const helperPath = path.join(__dirname, "..", "print_helper.exe");

function normalizeText(text) {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[¡¿]/g, "")
    .replace(/[–—]/g, "-")
    .replace(/°C/g, "C").replace(/°/g, "")
    .toUpperCase();
}

router.post("/voucher", (req, res) => {
  const { lines } = req.body;
  if (!lines || !Array.isArray(lines) || lines.length === 0) {
    return res.status(400).json({ error: "Se requieren lineas de texto" });
  }

  const normalized = lines.map(l => normalizeText(l));

  const child = execFile(helperPath, normalized, { timeout: 10000 }, (err, stdout, stderr) => {
    if (err) {
      console.error("Error al imprimir:", err.message, stderr);
      return res.status(500).json({ error: "Error al imprimir", detail: stderr || err.message });
    }
    res.json({ success: true });
  });
});

router.post("/test", (req, res) => {
  const testLines = [
    "\\C\\INVERSIONES CREDIARANCEL",
    "\\C\\TEST DE IMPRESION",
    "- - - - - - - - - - - - - - - -",
    "Fecha: " + new Date().toLocaleDateString("es-PE"),
    "Hora: " + new Date().toLocaleTimeString("es-PE"),
    "- - - - - - - - - - - - - - - -",
    "\\C\\Si ves esto, la impresora",
    "\\C\\funciona correctamente!",
    "",
    "Gracias por su preferencia"
  ];

  const child = execFile(helperPath, testLines, { timeout: 10000 }, (err, stdout, stderr) => {
    if (err) {
      return res.status(500).json({ error: "Error al imprimir", detail: stderr || err.message });
    }
    res.json({ success: true });
  });
});

module.exports = router;
