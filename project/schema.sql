DROP TABLE IF EXISTS App_user;

CREATE TABLE App_user (user_id text PRIMARY KEY,
                                name text NOT NULL,
                                email text NOT NULL,
                                picture text);

DROP TABLE IF EXISTS transaction;

CREATE TABLE transaction (transaction_id serial PRIMARY KEY,
                                amount integer NOT NULL,
                                created_time date DEFAULT CURRENT_TIMESTAMP,
                                title text NOT NULL,
                                description text,
                                type text,
                                user_id text NOT NULL);