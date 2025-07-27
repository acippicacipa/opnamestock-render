-- Disarankan untuk menghapus atau tidak menggunakan BEGIN TRANSACTION/COMMIT di MySQL untuk DDL (Data Definition Language).
-- Setiap statement CREATE TABLE dieksekusi secara terpisah.

-- Tabel `users` (diganti dari `user` untuk menghindari reserved keyword)
CREATE TABLE IF NOT EXISTS `users` (
    `id`            INT PRIMARY KEY AUTO_INCREMENT,
    `username`      VARCHAR(80) NOT NULL UNIQUE,
    `email`         VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabel `products`
CREATE TABLE IF NOT EXISTS `products` (
    `id`            INT PRIMARY KEY AUTO_INCREMENT,
    `kode_produk`   VARCHAR(50) NOT NULL UNIQUE,
    `nama_produk`   VARCHAR(200) NOT NULL,
    `saldo_awal`    INT NOT NULL DEFAULT 0,
    `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabel `stock_opname_sessions`
-- Dibuat SEBELUM `stock_opname_details` karena akan direferensikan.
CREATE TABLE IF NOT EXISTS `stock_opname_sessions` (
    `id`            INT PRIMARY KEY AUTO_INCREMENT,
    `lokasi`        VARCHAR(200) NOT NULL,
    `waktu_mulai`   DATETIME DEFAULT CURRENT_TIMESTAMP,
    `waktu_selesai` DATETIME NULL,
    `status`        VARCHAR(20) NOT NULL DEFAULT 'ongoing',
    `created_by_id` INT NULL,
    `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT `fk_sessions_users`
        FOREIGN KEY (`created_by_id`) REFERENCES `users`(`id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabel `stock_opname_details`
-- Tabel ini dibuat terakhir karena merujuk ke `products` dan `stock_opname_sessions`.
CREATE TABLE IF NOT EXISTS `stock_opname_details` (
    `id`            INT PRIMARY KEY AUTO_INCREMENT,
    `session_id`    INT NOT NULL,
    `product_id`    INT NOT NULL,
    `jumlah_barang` INT NOT NULL,
    `catatan`       TEXT,
    `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT `fk_details_session`
        FOREIGN KEY (`session_id`) REFERENCES `stock_opname_sessions`(`id`)
        ON DELETE CASCADE,
        
    CONSTRAINT `fk_details_product`
        FOREIGN KEY (`product_id`) REFERENCES `products`(`id`)
        ON DELETE RESTRICT,
        
    -- Constraint untuk memastikan produk unik per sesi
    CONSTRAINT `uq_detail_session_product`
        UNIQUE (`session_id`, `product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Membuat INDEX untuk meningkatkan performa query pada foreign key
-- Di MySQL, Primary Key dan Unique Constraint sudah otomatis dibuatkan index.
-- Namun, membuat index pada foreign key secara eksplisit adalah praktik yang baik.
CREATE INDEX `idx_details_session_id` ON `stock_opname_details` (`session_id`);
CREATE INDEX `idx_details_product_id` ON `stock_opname_details` (`product_id`);
CREATE INDEX `idx_sessions_created_by_id` ON `stock_opname_sessions` (`created_by_id`);

