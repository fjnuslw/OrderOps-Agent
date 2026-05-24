CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TIMESTAMP,
    price NUMERIC,
    freight_value NUMERIC,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS payments (
    order_id TEXT,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value NUMERIC
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_weight_g NUMERIC,
    product_length_cm NUMERIC,
    product_height_cm NUMERIC,
    product_width_cm NUMERIC
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT PRIMARY KEY,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    order_id TEXT,
    customer_id TEXT,
    seller_id TEXT,
    scenario TEXT,
    priority TEXT,
    status TEXT,
    created_at TIMESTAMP,
    title TEXT,
    description TEXT,
    expected_action TEXT,
    risk_level TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    ticket_id TEXT,
    requested_by TEXT,
    status TEXT,
    reason TEXT,
    created_at TIMESTAMP,
    decided_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_call_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT,
    tool_name TEXT,
    args_json JSONB,
    result_json JSONB,
    status TEXT,
    latency_ms INTEGER,
    error_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eval_cases (
    case_id TEXT PRIMARY KEY,
    scenario TEXT,
    user_query TEXT,
    selector_sql TEXT,
    expected_tools JSONB,
    expected_decision TEXT,
    risk_level TEXT,
    approval_required BOOLEAN
);
