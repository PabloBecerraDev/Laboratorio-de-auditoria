-- Nortia Distribuciones S.A.S. - laboratorio de auditoria
-- Separa el portal principal (gobernado) del portal legacy de proveedores
-- (heredado de una fusion, nunca migrado al mismo esquema de control de accesos).

CREATE SCHEMA IF NOT EXISTS portal;
CREATE SCHEMA IF NOT EXISTS legacy;
