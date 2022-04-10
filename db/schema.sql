CREATE TABLE addresses(
    first_name text,
    last_name text,
    address_line_1 text,
    address_line_2 text,
    city text,
    post_code text,
    unique(
        first_name,
        last_name,
        address_line_1,
        address_line_2,
        city,
        post_code
    )
);
