const express = require("express");
const cors = require("cors");
const path = require("path");

const app = express();
const clientesRoutes = require("./routes/clientes");
const creditosRoutes = require("./routes/creditos");
const pagosRoutes = require("./routes/pagos");
const authRoutes = require("./routes/auth");
const printRoutes = require("./routes/print");
const exportRoutes = require("./routes/export");
const dashboardRoutes = require("./routes/dashboard");
const cajaRoutes = require("./routes/caja");
const respaldosRoutes = require("./routes/respaldos");
const reportesRoutes = require("./routes/reportes");
const evaluacionRoutes = require("./routes/evaluacion");

app.use(cors());
app.use(express.json());
app.use("/api/clientes", clientesRoutes);
app.use("/api/creditos", creditosRoutes);
app.use("/api/pagos", pagosRoutes);
app.use("/api/auth", authRoutes);
app.use("/api/print", printRoutes);
app.use("/api/export", exportRoutes);
app.use("/api/dashboard", dashboardRoutes);
app.use("/api/caja", cajaRoutes);
app.use("/api/respaldos", respaldosRoutes);
app.use("/api/reportes", reportesRoutes);
app.use("/api/evaluacion", evaluacionRoutes);
app.use("/frontend", express.static(path.join(__dirname, "..", "frontend")));

app.get("/", (req, res) => {
    res.send("Servidor CrediArancel funcionando");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => {
    console.log(`Servidor corriendo en puerto ${PORT}`);
});