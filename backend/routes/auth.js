const express = require("express");
const router = express.Router();
const { promisify } = require("util");
const db = require("../db");
const query = promisify(db.query).bind(db);

router.post("/login", async (req, res) => {
    try {
        const { usuario, password } = req.body;

        if (!usuario || !password) {
            return res.status(400).json({ mensaje: "Completa todos los campos" });
        }

        let rows;
        try {
            rows = await query(
                "SELECT id, usuario, nombre, rol FROM usuarios WHERE usuario = ? AND password = ?",
                [usuario, password]
            );
        } catch (e) {
            rows = await query(
                "SELECT id, usuario, usuario AS nombre, rol FROM usuarios WHERE usuario = ? AND password = ?",
                [usuario, password]
            );
        }

        if (rows.length === 0) {
            return res.status(401).json({ mensaje: "Usuario o contraseña incorrectos" });
        }

        res.json({
            mensaje: "Inicio de sesión exitoso",
            usuario: rows[0].usuario,
            nombre: rows[0].nombre || rows[0].usuario,
            rol: rows[0].rol
        });
    } catch (error) {
        console.error("Error en login:", error);
        res.status(500).json({ mensaje: "Error del servidor" });
    }
});

module.exports = router;
