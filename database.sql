CREATE DATABASE IF NOT EXISTS `gastos_personales`;
USE `gastos_personales`;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(60) NOT NULL,
  `email` varchar(60) NOT NULL,
  `password_usuario` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabla de categorías
CREATE TABLE IF NOT EXISTS `categorias` (
  `id_categoria` int NOT NULL AUTO_INCREMENT,
  `nombre_categoria` varchar(60) DEFAULT NULL,
  `tipo` enum('gasto','ingreso') NOT NULL,
  PRIMARY KEY (`id_categoria`),
  UNIQUE KEY `nombre_categoria` (`nombre_categoria`,`tipo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabla de gastos
CREATE TABLE IF NOT EXISTS `gastos` (
  `id_gasto` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `id_categoria` int NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` datetime NOT NULL,
  `notas` varchar(150) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT '1',
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id_gasto`),
  KEY `id_usuario` (`id_usuario`),
  KEY `id_categoria` (`id_categoria`),
  CONSTRAINT `gastos_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`),
  CONSTRAINT `gastos_ibfk_2` FOREIGN KEY (`id_categoria`) REFERENCES `categorias` (`id_categoria`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabla de presupuestos
CREATE TABLE IF NOT EXISTS `presupuestos` (
  `id_presupuesto` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `id_categoria` int NOT NULL,
  `monto_limite` decimal(10,2) DEFAULT NULL,
  `periodo` enum('semanal','mensual','proyecto') NOT NULL,
  PRIMARY KEY (`id_presupuesto`),
  UNIQUE KEY `id_usuario` (`id_usuario`,`id_categoria`,`periodo`),
  KEY `id_categoria` (`id_categoria`),
  CONSTRAINT `presupuestos_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`),
  CONSTRAINT `presupuestos_ibfk_2` FOREIGN KEY (`id_categoria`) REFERENCES `categorias` (`id_categoria`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tipos de alerta
CREATE TABLE IF NOT EXISTS `tipos_alerta` (
  `id_tipo_alerta` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `plantilla` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id_tipo_alerta`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Alertas generadas
CREATE TABLE IF NOT EXISTS `alertas` (
  `id_alerta` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `id_tipo_alerta` int NOT NULL,
  `mensaje` varchar(150) DEFAULT NULL,
  `leida` tinyint(1) DEFAULT '0',
  `fecha` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_alerta`),
  KEY `id_usuario` (`id_usuario`),
  KEY `id_tipo_alerta` (`id_tipo_alerta`),
  CONSTRAINT `alertas_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`),
  CONSTRAINT `alertas_ibfk_2` FOREIGN KEY (`id_tipo_alerta`) REFERENCES `tipos_alerta` (`id_tipo_alerta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Historial de cambios de gastos
CREATE TABLE IF NOT EXISTS `gastos_historial` (
  `id_historial` int NOT NULL AUTO_INCREMENT,
  `id_gasto` int NOT NULL,
  `accion` enum('INSERT','UPDATE','DELETE') NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` datetime DEFAULT CURRENT_TIMESTAMP,
  `id_usuario_accion` int NOT NULL,
  `descripcion_cambio` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_historial`),
  KEY `id_gasto` (`id_gasto`),
  KEY `id_usuario_accion` (`id_usuario_accion`),
  CONSTRAINT `gastos_historial_ibfk_1` FOREIGN KEY (`id_gasto`) REFERENCES `gastos` (`id_gasto`),
  CONSTRAINT `gastos_historial_ibfk_2` FOREIGN KEY (`id_usuario_accion`) REFERENCES `usuarios` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Datos iniciales de ejemplo

INSERT INTO usuarios (nombre, email, password_usuario)
VALUES
('Administrador Demo', 'admin@demo.local', 'password_demo');

INSERT INTO categorias (nombre_categoria, tipo) VALUES
('Alimentación', 'gasto'),
('Transporte', 'gasto'),
('Servicios', 'gasto'),
('Tecnología', 'gasto'),
('Salud', 'gasto'),
('Herramientas Digitales', 'gasto');


INSERT INTO presupuestos (id_usuario, id_categoria, monto_limite, periodo) VALUES 
(1, 1, 3500, 'mensual'),
(1, 2, 2000, 'mensual'),
(1, 3, 2500, 'mensual'),
(1, 4, 800, 'mensual'),
(1, 5, 1500, 'mensual'),
(1, 6, 4000, 'mensual');
-- Los presupuestos asumen el orden de inserción de categorías definido arriba


INSERT INTO tipos_alerta (nombre, plantilla) VALUES 
('presupuesto_excedido', 'Has superado el presupuesto establecido. Total gastado: {total} | Límite: {limite}'),
('umbral_presupuesto', 'Has alcanzado el {porcentaje}% del presupuesto asignado a {categoria}'),
('gasto_atipico', 'Se detectó un gasto inusual de {monto}, superior al promedio histórico de {promedio}');
