const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);
const { exec } = require("child_process");
const path = require("path");

router.get("/exportar", (req, res) => {
    const backupDir = path.join(__dirname, "..", "backups");
    const fs = require("fs");
    if (!fs.existsSync(backupDir)) fs.mkdirSync(backupDir, { recursive: true });
    const filename = `crediarancel_backup_${new Date().toISOString().slice(0,10).replace(/-/g,"")}.sql`;
    const filepath = path.join(backupDir, filename);
    const cmd = `"C:\\xampp\\mysql\\bin\\mysqldump" -u root crediarancel_db > "${filepath}"`;
    exec(cmd, (err) => {
        if (err) return res.status(500).json({ mensaje: "Error al exportar", error: err.message });
        res.download(filepath, filename);
    });
});

module.exports = router;
