-- I have used SQL queries inside my backend code,
-- so I created this file to show the database structure used.

create database chat;
use chat;

-- stores urls and their vector index
create table data_url (
    id int auto_increment primary key,
    url text,
    vd_index varchar(100)
);

-- stores user queries and responses
create table messages (
    id int auto_increment primary key,
    prompt text,
    response text,
    data_id int,
    tim timestamp default current_timestamp,
    foreign key (data_id) references data_url(id)
);

-- sample data (just for testing)
insert into data_url (url, vd_index) values
('https://example.com', 'index-1');

insert into messages (prompt, response, data_id) values
('what is this site', 'it is a demo site', 1);

-- fetch chat history
select m.id, m.prompt, m.response, m.tim, d.url
from messages m
join data_url d on m.data_id = d.id
order by m.tim desc;