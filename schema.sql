-- APP: accounts MIGRATION: 0001_initial
--
-- Create model User
--
CREATE TABLE `Users` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `password` varchar(128) NOT NULL, `last_login` datetime(6) NULL, `is_superuser` bool NOT NULL, `full_name` varchar(100) NOT NULL, `email` varchar(100) NOT NULL UNIQUE, `matric_number` varchar(30) NULL UNIQUE, `role` varchar(20) NOT NULL, `is_active` bool NOT NULL, `is_staff` bool NOT NULL, `date_registered` datetime(6) NOT NULL);
CREATE TABLE `Users_groups` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `user_id` bigint NOT NULL, `group_id` integer NOT NULL);
CREATE TABLE `Users_user_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `user_id` bigint NOT NULL, `permission_id` integer NOT NULL);
ALTER TABLE `Users_groups` ADD CONSTRAINT `Users_groups_user_id_group_id_590dc796_uniq` UNIQUE (`user_id`, `group_id`);
ALTER TABLE `Users_groups` ADD CONSTRAINT `Users_groups_user_id_d0013979_fk_Users_id` FOREIGN KEY (`user_id`) REFERENCES `Users` (`id`);
ALTER TABLE `Users_groups` ADD CONSTRAINT `Users_groups_group_id_2ddde7ed_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `Users_user_permissions` ADD CONSTRAINT `Users_user_permissions_user_id_permission_id_f5781f04_uniq` UNIQUE (`user_id`, `permission_id`);
ALTER TABLE `Users_user_permissions` ADD CONSTRAINT `Users_user_permissions_user_id_c976b39e_fk_Users_id` FOREIGN KEY (`user_id`) REFERENCES `Users` (`id`);
ALTER TABLE `Users_user_permissions` ADD CONSTRAINT `Users_user_permissio_permission_id_7995fa19_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);


-- APP: catalogue MIGRATION: 0001_initial
--
-- Create model Category
--
CREATE TABLE `catalogue_category` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `category_name` varchar(100) NOT NULL UNIQUE, `code` varchar(10) NOT NULL);
--
-- Create model Book
--
CREATE TABLE `catalogue_book` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `author` varchar(150) NOT NULL, `isbn` varchar(20) NOT NULL, `cover_image` varchar(100) NULL, `description` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `category_id` bigint NOT NULL);
--
-- Create model Copy
--
CREATE TABLE `catalogue_copy` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `whereabouts` varchar(100) NOT NULL, `status` varchar(20) NOT NULL, `date_added` datetime(6) NOT NULL, `book_id` bigint NOT NULL);
--
-- Create index catalogue_b_title_af9179_idx on field(s) title of model book
--
CREATE INDEX `catalogue_b_title_af9179_idx` ON `catalogue_book` (`title`);
--
-- Create index catalogue_b_author_207052_idx on field(s) author of model book
--
CREATE INDEX `catalogue_b_author_207052_idx` ON `catalogue_book` (`author`);
--
-- Create index catalogue_b_isbn_fa8ee3_idx on field(s) isbn of model book
--
CREATE INDEX `catalogue_b_isbn_fa8ee3_idx` ON `catalogue_book` (`isbn`);
ALTER TABLE `catalogue_book` ADD CONSTRAINT `catalogue_book_category_id_956e091a_fk_catalogue_category_id` FOREIGN KEY (`category_id`) REFERENCES `catalogue_category` (`id`);
CREATE INDEX `catalogue_book_title_08816623` ON `catalogue_book` (`title`);
CREATE INDEX `catalogue_book_author_427c7b28` ON `catalogue_book` (`author`);
CREATE INDEX `catalogue_book_isbn_c51a0597` ON `catalogue_book` (`isbn`);
ALTER TABLE `catalogue_copy` ADD CONSTRAINT `catalogue_copy_book_id_d6e473d6_fk_catalogue_book_id` FOREIGN KEY (`book_id`) REFERENCES `catalogue_book` (`id`);
CREATE INDEX `catalogue_copy_status_3edc40f8` ON `catalogue_copy` (`status`);


-- APP: circulation MIGRATION: 0001_initial
--
-- Create model BorrowRecord
--
CREATE TABLE `circulation_borrowrecord` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `borrow_date` date NOT NULL, `due_date` date NOT NULL, `return_date` date NULL, `renewal_count` smallint UNSIGNED NOT NULL CHECK (`renewal_count` >= 0), `copy_id` bigint NOT NULL, `issued_by_id` bigint NOT NULL);
ALTER TABLE `circulation_borrowrecord` ADD CONSTRAINT `circulation_borrowrecord_copy_id_4ed2c7e4_fk_catalogue_copy_id` FOREIGN KEY (`copy_id`) REFERENCES `catalogue_copy` (`id`);
ALTER TABLE `circulation_borrowrecord` ADD CONSTRAINT `circulation_borrowrecord_issued_by_id_063ec5f6_fk_Users_id` FOREIGN KEY (`issued_by_id`) REFERENCES `Users` (`id`);


-- APP: reservations MIGRATION: 0001_initial
--
-- Create model Reservation
--
CREATE TABLE `reservations_reservation` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `reservation_date` datetime(6) NOT NULL, `status` varchar(20) NOT NULL, `notified_at` datetime(6) NULL, `expires_at` datetime(6) NULL, `book_id` bigint NOT NULL, `copy_id` bigint NULL, `student_id` bigint NOT NULL);
ALTER TABLE `reservations_reservation` ADD CONSTRAINT `reservations_reservation_book_id_42ea7d31_fk_catalogue_book_id` FOREIGN KEY (`book_id`) REFERENCES `catalogue_book` (`id`);
ALTER TABLE `reservations_reservation` ADD CONSTRAINT `reservations_reservation_copy_id_729b5765_fk_catalogue_copy_id` FOREIGN KEY (`copy_id`) REFERENCES `catalogue_copy` (`id`);
ALTER TABLE `reservations_reservation` ADD CONSTRAINT `reservations_reservation_student_id_8ff232f7_fk_Users_id` FOREIGN KEY (`student_id`) REFERENCES `Users` (`id`);
CREATE INDEX `reservation_book_id_561ea0_idx` ON `reservations_reservation` (`book_id`, `status`, `reservation_date`);


-- APP: reservations MIGRATION: 0002_reservation_unique_active_reservation_per_student_book
--
-- Create constraint unique_active_reservation_per_student_book on model reservation
--
-- (no-op)


-- APP: fines MIGRATION: 0001_initial
--
-- Create model Fine
--
CREATE TABLE `fines_fine` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `amount` numeric(10, 2) NOT NULL, `status` varchar(20) NOT NULL, `date_created` date NOT NULL, `date_paid` date NULL, `payment_reference` varchar(50) NOT NULL, `waiver_reason` varchar(200) NOT NULL, `borrow_record_id` bigint NOT NULL, `recorded_by_id` bigint NULL);
ALTER TABLE `fines_fine` ADD CONSTRAINT `fines_fine_borrow_record_id_55d78f06_fk_circulati` FOREIGN KEY (`borrow_record_id`) REFERENCES `circulation_borrowrecord` (`id`);
ALTER TABLE `fines_fine` ADD CONSTRAINT `fines_fine_recorded_by_id_7ded248e_fk_Users_id` FOREIGN KEY (`recorded_by_id`) REFERENCES `Users` (`id`);


-- APP: notifications MIGRATION: 0001_initial
--
-- Create model Notification
--
CREATE TABLE `notifications_notification` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `type` varchar(30) NOT NULL, `channel` varchar(10) NOT NULL, `message` varchar(500) NOT NULL, `is_read` bool NOT NULL, `date_sent` datetime(6) NOT NULL, `borrow_record_id` bigint NULL);
ALTER TABLE `notifications_notification` ADD CONSTRAINT `notifications_notifi_borrow_record_id_ce6155ab_fk_circulati` FOREIGN KEY (`borrow_record_id`) REFERENCES `circulation_borrowrecord` (`id`);


-- APP: core MIGRATION: 0001_initial
--
-- Create model SystemLog
--
CREATE TABLE `core_systemlog` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `timestamp` datetime(6) NOT NULL, `action` varchar(50) NOT NULL, `detail` varchar(300) NOT NULL, `user_id` bigint NULL);
ALTER TABLE `core_systemlog` ADD CONSTRAINT `core_systemlog_user_id_4765722c_fk_Users_id` FOREIGN KEY (`user_id`) REFERENCES `Users` (`id`);
CREATE INDEX `core_systemlog_timestamp_17ed86f0` ON `core_systemlog` (`timestamp`);
CREATE INDEX `core_systemlog_action_eba3ddff` ON `core_systemlog` (`action`);


