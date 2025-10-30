CREATE DATABASE IF NOT EXISTS beauty_center;
USE beauty_center;

-- Roles del sistema
CREATE TABLE role (
    id_role INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Nombre del rol: empleado, cliente',
    description VARCHAR(100),
    state BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_role_name ON role (name);

-- Cuentas de usuario
CREATE TABLE user_account (
    id_user INT AUTO_INCREMENT PRIMARY KEY,
    id_role INT NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    is_logged_in BOOLEAN NOT NULL DEFAULT FALSE,
    state BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_role) REFERENCES role(id_role)
);
CREATE INDEX idx_user_email ON user_account (email);
CREATE INDEX idx_user_role ON user_account (id_role);

-- Perfil de usuario
CREATE TABLE user_profile (
    id_profile INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    state BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_user) REFERENCES user_account(id_user)
);
CREATE INDEX idx_profile_user ON user_profile (id_user);

-- Servicios ofrecidos
CREATE TABLE service (
    id_service INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    state BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_service_name ON service (name);

-- Estados de las reservas
CREATE TABLE reservation_status (
    id_reservation_status INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Pendiente, Confirmado, Cancelado, Completado',
    state BOOLEAN NOT NULL DEFAULT TRUE
);

-- Reservas de clientes (actualizado)
CREATE TABLE reservation (
    id_reservation INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL COMMENT 'Cliente que hizo la reserva',
    id_service INT NOT NULL,
    id_reservation_status INT NOT NULL DEFAULT 1,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_price DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL COMMENT 'ej., Efectivo, Tarjeta, Transferencia (ficticio)',
    state BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_user) REFERENCES user_account(id_user),
    FOREIGN KEY (id_service) REFERENCES service(id_service) ON DELETE CASCADE,  -- Aquí se agrega ON DELETE CASCADE
    FOREIGN KEY (id_reservation_status) REFERENCES reservation_status(id_reservation_status)
);
CREATE INDEX idx_reservation_user ON reservation (id_user);
CREATE INDEX idx_reservation_service ON reservation (id_service);
CREATE INDEX idx_reservation_start_date ON reservation (start_datetime);

-- Crear tabla de servicios eliminados
CREATE TABLE deleted_services (
    id_deleted_service INT AUTO_INCREMENT PRIMARY KEY,
    id_service INT NOT NULL,
    id_user INT NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_service) REFERENCES service(id_service),
    FOREIGN KEY (id_user) REFERENCES user_account(id_user)
);

-- Crear trigger para manejar la eliminación
DELIMITER //

CREATE TRIGGER before_service_delete
BEFORE DELETE ON service
FOR EACH ROW
BEGIN
    INSERT INTO deleted_services (id_service, id_user)
    SELECT OLD.id_service, r.id_user
    FROM reservation r
    WHERE r.id_service = OLD.id_service;
END;
//

DELIMITER ;

-- Bloques del calendario (nueva tabla)
CREATE TABLE calendar_block (
    id_block INT AUTO_INCREMENT PRIMARY KEY,
    id_reservation INT NULL,
    title VARCHAR(100) NOT NULL,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    color VARCHAR(20) DEFAULT '#ffb3b3',
    type ENUM('reservation', 'manual', 'maintenance') DEFAULT 'reservation',
    state BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_reservation) REFERENCES reservation(id_reservation)
);

-- Recordatorios automáticos
CREATE TABLE reminder (
    id_reminder INT AUTO_INCREMENT PRIMARY KEY,
    id_reservation INT NOT NULL,
    reminder_datetime DATETIME NOT NULL COMMENT 'Cuándo enviar el recordatorio',
    message VARCHAR(255) NOT NULL COMMENT 'Mensaje de recordatorio para el cliente',
    state BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_reservation) REFERENCES reservation(id_reservation)
);
CREATE INDEX idx_reminder_reservation ON reminder (id_reservation);
CREATE INDEX idx_reminder_datetime ON reminder (reminder_datetime);


-- Contiene los datos válidos de cada hoja
CREATE TABLE data_imported (
    id_import INT AUTO_INCREMENT PRIMARY KEY,
    sheet_name VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    duration_minutes INT,
    price DECIMAL(10,2),
    state BOOLEAN,
    user_id INT NOT NULL,  -- Nueva columna añadida
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contiene los errores detectados durante la carga
CREATE TABLE data_errors (
    id_error INT AUTO_INCREMENT PRIMARY KEY,
    sheet_name VARCHAR(100) NOT NULL,
    row_num INT,
    error_message TEXT,
    user_id INT NOT NULL,  -- Nueva columna añadida
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_imported_user_sheet ON data_imported (user_id, sheet_name);
CREATE INDEX idx_data_errors_user_sheet ON data_errors (user_id, sheet_name);


-- Datos iniciales
INSERT INTO role (name, description) VALUES
('empleado', 'Empleado del salón con acceso limitado'),
('cliente', 'Cliente que puede hacer reservas');

INSERT INTO user_account (id_role, email, password, is_logged_in, state)
VALUES (
    1,
    'admin@example.com',
    '$2b$12$toDoqsuu1QWr2TMAhy4WGORUbxnbddu6XIguPY90dZSC3tf70uLW6',  -- hash de 'admin123'
    FALSE,
    TRUE
);

INSERT INTO reservation_status (name) VALUES
('Pendiente'),
('Confirmado'),
('Cancelado'),
('Completado');
