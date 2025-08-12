CREATE TABLE historico_ipca (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    vencimento DATE NOT NULL,
    rendimento_real NUMERIC NOT NULL
);

INSERT INTO historico_ipca (data, vencimento, rendimento_real) VALUES
('2020-01-01', '2045-01-01', 5.1),
('2021-01-01', '2045-01-01', 6.0),
('2022-01-01', '2045-01-01', 5.8),
('2023-01-01', '2045-01-01', 6.3),
('2024-01-01', '2045-01-01', 5.9);
