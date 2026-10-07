-- Proposta para o banco TRANSFORMAÇÃODIGITAL_JOST.
-- Aplicação depende de revisão e autorização específicas do responsável pelo banco.
CREATE TABLE dbo.DJ_EVENTS (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_EVENTS PRIMARY KEY,
    name NVARCHAR(120) NOT NULL,
    description NVARCHAR(2000) NOT NULL,
    created_by NVARCHAR(128) NOT NULL,
    created_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_EVENTS_created_at DEFAULT SYSUTCDATETIME()
);
