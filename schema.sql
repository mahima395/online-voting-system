-- Online Voting System database schema (MySQL 8)
-- Import with: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS voting_system
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE voting_system;

-- Registered voters
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    username      VARCHAR(30)  NOT NULL,
    email         VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

-- Administrators (created with create_admin.py, never with a fixed password)
CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(30)  NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_admins_username (username)
) ENGINE=InnoDB;

-- Candidates
CREATE TABLE IF NOT EXISTS candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    party       VARCHAR(100) NOT NULL DEFAULT '',
    description VARCHAR(500) NOT NULL DEFAULT '',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_candidates_name (name)
) ENGINE=InnoDB;

-- Votes: UNIQUE(user_id) lets the database itself block a second vote.
-- RESTRICT stops a candidate who already has votes from being deleted,
-- so votes can never be removed by accident.
CREATE TABLE IF NOT EXISTS votes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT       NOT NULL,
    candidate_id INT       NOT NULL,
    voted_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_votes_user (user_id),
    CONSTRAINT fk_votes_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_votes_candidate
        FOREIGN KEY (candidate_id) REFERENCES candidates (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;
