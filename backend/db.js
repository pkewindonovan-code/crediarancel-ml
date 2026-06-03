const mysql = require("mysql2");

const conexion = mysql.createConnection({
    host: process.env.DB_HOST || "localhost",
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD || "",
    database: process.env.DB_NAME || "crediarancel_db",
    port: process.env.DB_PORT || 3306,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

conexion.connect((error) => {
    if (error) {
        console.log("Error de conexión:", error);
    } else {
        console.log("MySQL conectado a " + (process.env.DB_HOST || "localhost"));
    }
});

module.exports = conexion;