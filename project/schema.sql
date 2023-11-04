-- DROP TABLE IF EXISTS App_user;
-- DROP TABLE IF EXISTS Post;
-- DROP TABLE IF EXISTS Question;
-- DROP TABLE IF EXISTS Response;
-- DROP TABLE IF EXISTS AI_chat;
-- DROP TABLE IF EXISTS Chat_message;
-- DROP TABLE IF EXISTS Comment;
-- DROP TABLE IF EXISTS Image;
-- DROP TABLE IF EXISTS Tag;
-- DROP TABLE IF EXISTS Related_content;
-- DROP TABLE IF EXISTS Related_web_link;
-- DROP TABLE IF EXISTS Similar_question;
-- DROP TABLE IF EXISTS Related_video;
-- DROP TABLE IF EXISTS User_Tag;
-- DROP TABLE IF EXISTS Follow;
-- DROP TABLE IF EXISTS Post_Like;
-- DROP TABLE IF EXISTS Question_Tag;
-- DROP TABLE IF EXISTS Post_Image;

CREATE TABLE IF NOT EXISTS App_user  ( 
    user_id serial PRIMARY KEY,
    username text NOT NULL,
    name text NOT NULL,
    about text,
    picture_url text,
    badge text DEFAULT 'beginner',
    email text,
    google_id bigint, 
    facebook_id bigint,
    github_id bigint,
    password text,
    account_creation_datetime date DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Post  (
    post_id serial PRIMARY KEY,
    type text DEFAULT 'question', --might not need this ("question", "response")
    vote_counter integer DEFAULT 0,
    created_time date DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Question  (
    question_id serial PRIMARY KEY,
    post_id integer, 
    user_id integer, 
    question_text text NOT NULL,

    CONSTRAINT fk_question_post
        FOREIGN KEY(post_id) 
        REFERENCES Post(post_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_question_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Response  (
    response_id serial PRIMARY KEY,
    post_id integer,
    question_id integer, 
    response_text text NOT NULL, 
    user_id integer DEFAULT 0, --user 0 = AI chat bot
    chat_id integer DEFAULT -1, --default chat id = -1, AI chat not available

    CONSTRAINT fk_response_post
        FOREIGN KEY(post_id) 
        REFERENCES Post(post_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_response_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_response_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS AI_chat  (
    chat_id serial PRIMARY KEY,
    response_id integer,
    title text,
    created_time date DEFAULT CURRENT_TIMESTAMP,

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
    created_time date DEFAULT CURRENT_TIMESTAMP,

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
    created_time date DEFAULT CURRENT_TIMESTAMP,
    
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
    alt_text text
);

CREATE TABLE IF NOT EXISTS Tag  (
    tag_id serial PRIMARY KEY,
    tag_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS Related_content  (
    related_content_id serial PRIMARY KEY,
    question_id integer,

    CONSTRAINT fk_web_link_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Related_web_link  (
    related_web_link_url text NOT NULL
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS Similar_question  (
    similar_question_id integer NOT NULL,

    CONSTRAINT fk_similar_question_question
        FOREIGN KEY(similar_question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS Related_video  (
    related_video_url text NOT NULL
) INHERITS (Related_content);

CREATE TABLE IF NOT EXISTS User_Tag  (
    tag_id integer,
    user_id integer,

    CONSTRAINT fk_user_tag_tag
        FOREIGN KEY(tag_id) 
        REFERENCES Tag(tag_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_tag_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (tag_id, user_id)
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

CREATE TABLE IF NOT EXISTS Post_Like  (
    post_id integer,
    user_id integer,

    CONSTRAINT fk_post_like_post
        FOREIGN KEY(post_id) 
        REFERENCES Post(post_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_post_like_app_user
        FOREIGN KEY(user_id) 
        REFERENCES App_user(user_id)
        ON DELETE CASCADE,

    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS Question_Tag  (
    tag_id integer,
    question_id integer,

    CONSTRAINT fk_question_tag_tag
        FOREIGN KEY(tag_id) 
        REFERENCES Tag(tag_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_question_tag_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE,

    PRIMARY KEY (tag_id, question_id)
);

CREATE TABLE IF NOT EXISTS Post_Image  (
    post_id integer,
    image_id integer,

    CONSTRAINT fk_post_image_post
        FOREIGN KEY(post_id) 
        REFERENCES Post(post_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_post_image_image
        FOREIGN KEY(image_id) 
        REFERENCES Image(image_id)
        ON DELETE CASCADE,

    PRIMARY KEY (post_id, image_id)
);