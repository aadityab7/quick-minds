DROP TABLE IF EXISTS App_user CASCADE;
DROP TABLE IF EXISTS Post CASCADE;
DROP TABLE IF EXISTS Question CASCADE;
DROP TABLE IF EXISTS Response CASCADE;
DROP TABLE IF EXISTS AI_chat CASCADE;
DROP TABLE IF EXISTS Chat_message CASCADE;
DROP TABLE IF EXISTS Comment CASCADE;
DROP TABLE IF EXISTS Image CASCADE;
DROP TABLE IF EXISTS Tag CASCADE;
DROP TABLE IF EXISTS Related_content CASCADE;
DROP TABLE IF EXISTS Related_web_search_results CASCADE;
DROP TABLE IF EXISTS Related_question CASCADE;
DROP TABLE IF EXISTS Related_video CASCADE;
DROP TABLE IF EXISTS User_Tag CASCADE;
DROP TABLE IF EXISTS Follow CASCADE;
DROP TABLE IF EXISTS Post_Vote CASCADE;
DROP TABLE IF EXISTS Question_Tag CASCADE;

CREATE TABLE IF NOT EXISTS App_user  ( 
    user_id serial PRIMARY KEY,
    username text,
    name text NOT NULL,
    about text,
    badge text DEFAULT 'beginner',
    email text,
    google_id text, 
    facebook_id text,
    github_id text,
    picture_url text,
    account_creation_datetime timestamp DEFAULT CURRENT_TIMESTAMP,
    password text
);

CREATE TABLE IF NOT EXISTS Post  (
    post_id serial PRIMARY KEY,
    type text DEFAULT 'question', --might not need this ("question", "response")
    vote_counter integer DEFAULT 0,
    response_counter integer DEFAULT 0,
    created_time timestamp DEFAULT CURRENT_TIMESTAMP,
    user_id integer NOT NULL,

    CONSTRAINT fk_post_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Question  (
    question_id serial PRIMARY KEY,
    question_title text NOT NULL,
    question_text text NOT NULL,
    tags text[5],
    document_vectors tsvector
) INHERITS (Post);

CREATE INDEX idx_question_doc_vec ON Question USING gin(document_vectors);

CREATE TABLE IF NOT EXISTS Response  (
    response_id serial PRIMARY KEY,
    question_id integer NOT NULL,
    response_text text NOT NULL,
    chat_id integer DEFAULT -1, --default chat id = -1, AI chat not available

    CONSTRAINT fk_response_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_response_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
) INHERITS (Post);

CREATE TABLE IF NOT EXISTS AI_chat  (
    chat_id serial PRIMARY KEY,
    response_id integer,
    title text,
    created_time timestamp DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ai_chat_response
        FOREIGN KEY(response_id) 
        REFERENCES Response(response_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Chat_message  (
    message_id serial PRIMARY KEY,
    chat_id integer,
    sender_user_id integer,
    message_text text,
    created_time timestamp DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_message_ai_chat
        FOREIGN KEY(chat_id)
        REFERENCES AI_chat(chat_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chat_message_app_user
        FOREIGN KEY(sender_user_id)
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Comment  (
    comment_id serial PRIMARY KEY,
    response_id integer, 
    user_id integer, 
    comment_text text NOT NULL, 
    created_time timestamp DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_comment_response
        FOREIGN KEY(response_id) 
        REFERENCES Response(response_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_comment_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Image  (
    image_id serial PRIMARY KEY,
    url text NOT NULL,
    alt_text text,
    question_id integer,
    response_id integer,
    post_type text DEFAULT 'question',

    CONSTRAINT fk_image_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_image_response
        FOREIGN KEY(response_id) 
        REFERENCES Response(response_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Tag  (
    tag_name text PRIMARY KEY,
    tag_description text,
    question_count integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Related_content  (
    related_content_id serial PRIMARY KEY,
    question_id integer NOT NULL,

    CONSTRAINT fk_web_link_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Related_web_search_result  (
    title text NOT NULL,
    description text NOT NULL,
    link text NOT NULL
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS Related_question  (
    similar_question_id integer NOT NULL,

    CONSTRAINT fk_similar_question_question
        FOREIGN KEY(similar_question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS Related_video  (
    title text  NOT NULL, 
    description text  NOT NULL, 
    video_url text  NOT NULL, 
    thumbnail_url text  NOT NULL, 
    channel_title text  NOT NULL, 
    player_embed_html text  NOT NULL
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS User_Tag  (
    tag_name text,
    user_id integer,

    CONSTRAINT fk_user_tag_tag
        FOREIGN KEY(tag_name) 
        REFERENCES Tag(tag_name)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_tag_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (tag_name, user_id)
);

CREATE TABLE IF NOT EXISTS Follow  (
    follower_user_id integer,
    followed_user_id integer,

    CONSTRAINT fk_follow_app_user_1
        FOREIGN KEY(follower_user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_follow_app_user_2
        FOREIGN KEY(followed_user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (follower_user_id, followed_user_id)
);

CREATE TABLE IF NOT EXISTS Post_Vote (
    question_id integer,
    response_id integer,
    user_id integer,
    val integer DEFAULT 1,

    CONSTRAINT fk_post_vote_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,
    
    CONSTRAINT fk_post_vote_response
        FOREIGN KEY(response_id) 
        REFERENCES Response(response_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_post_vote_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Question_Tag  (
    tag_name text,
    question_id integer,

    CONSTRAINT fk_question_tag_tag
        FOREIGN KEY(tag_name) 
        REFERENCES Tag(tag_name)
        ON DELETE CASCADE,

    CONSTRAINT fk_question_tag_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,

    PRIMARY KEY (tag_name, question_id)
);

INSERT INTO App_user 
    (user_id, username, name, about) 
VALUES 
    (0, 'google_vertex_ai', 'Google Vertex AI', 'Generative AI chat bot by Google which provides quick first response to user questions.');


CREATE TABLE Quiz (
    quiz_id serial PRIMARY KEY,
    user_id integer NOT NULL,
    created_time timestamp DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_quiz_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE Quiz_Question (
    quiz_question_id serial PRIMARY KEY, 
    quiz_id integer,
    question_text text,
    option_1 text,
    option_2 text,
    option_3 text,
    option_4 text,
    correct_answer integer,

    CONSTRAINT fk_quiz_question_quiz
        FOREIGN KEY(quiz_id) 
        REFERENCES Quiz(quiz_id)
        ON DELETE CASCADE
);

CREATE TABLE Quiz_Question_User_Response (
    quiz_question_id integer,
    user_id integer,
    user_response integer,

    CONSTRAINT fk_quiz_question_user_response_quiz_question
        FOREIGN KEY(quiz_question_id) 
        REFERENCES Quiz_Question(quiz_question_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_quiz_question_user_response_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (quiz_question_id, user_id)
);

CREATE TABLE Quiz_Score_Card (
    quiz_id integer, 
    user_id integer, 
    score integer,

    CONSTRAINT fk_quiz_score_card_quiz
        FOREIGN KEY(quiz_id) 
        REFERENCES Quiz(quiz_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_quiz_score_card_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (quiz_id, user_id)  
);