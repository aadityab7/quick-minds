-- DROP TABLE IF EXISTS App_user;
-- DROP TABLE IF EXISTS Post;
-- DROP TABLE IF EXISTS Question;
-- DROP TABLE IF EXISTS Response;
-- DROP TABLE IF EXISTS AI_chat;
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

CREATE TABLE App_user IF NOT EXISTS ( 
    user_id serial PRIMARY KEY,
    username text NOT NULL,
    name text NOT NULL,
    about text,
    picture_url text,
    email text,
    google_id bigint, 
    facebook_id bigint,
    github_id bigint,
    password text,
    account_creation_datetime date DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Post IF NOT EXISTS (
    post_id serial PRIMARY KEY,
    type text DEFAULT 'question', --might not need this ("question", "response")
    vote_counter integer DEFAULT 0,
    created_time date DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Question IF NOT EXISTS (
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

CREATE TABLE Response IF NOT EXISTS (
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

CREATE TABLE AI_chat IF NOT EXISTS (
    chat_id serial PRIMARY KEY,
    response_id integer,
    title text,
    created_time date DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ai_chat_response
        FOREIGN KEY(response_id) 
        REFERENCES Response(response_id)
        ON DELETE CASCADE
);

CREATE TABLE Comment IF NOT EXISTS (
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

CREATE TABLE Image IF NOT EXISTS (
    image_id serial PRIMARY KEY,
    url text NOT NULL,
    alt_text text
);

CREATE TABLE Tag IF NOT EXISTS (
    tag_id serial PRIMARY KEY,
    tag_name text NOT NULL
);

CREATE TABLE Related_content IF NOT EXISTS (
    related_content_id serial PRIMARY KEY,
    question_id integer,

    CONSTRAINT fk_web_link_question
        FOREIGN KEY(question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
);

CREATE TABLE Related_web_link IF NOT EXISTS (
    web_link_url text NOT NULL
) INHERITS (Related_content);

CREATE TABLE Similar_question IF NOT EXISTS (
    related_question_id integer NOT NULL,

    CONSTRAINT fk_similar_question_question
        FOREIGN KEY(similar_question_id) 
        REFERENCES Question(question_id)
        ON DELETE CASCADE
) INHERITS (Related_content);

CREATE TABLE Related_video IF NOT EXISTS (
    video_url text NOT NULL
) INHERITS (Related_content);

CREATE TABLE User_Tag IF NOT EXISTS (
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

CREATE TABLE Follow IF NOT EXISTS (
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

CREATE TABLE Post_Like IF NOT EXISTS (
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

CREATE TABLE Question_Tag IF NOT EXISTS (
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

CREATE TABLE Post_Image IF NOT EXISTS (
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