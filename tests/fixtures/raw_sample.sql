-- A day of every series, so the models and their tests run in CI against known
-- values rather than against whatever the source happened to publish.

TRUNCATE raw.xm_hourly, raw.load_audit;

INSERT INTO raw.xm_hourly (metric_id, entity, resource_code, tx_date, hour_values) VALUES
  ('PrecBolsNaci',   'Sistema', 'Sistema', DATE '2024-03-01',
   '{"Hour01":"350.10","Hour02":"351.20","Hour03":"349.90"}'),
  ('DemaReal',       'Sistema', 'Sistema', DATE '2024-03-01',
   '{"Hour01":"8800000","Hour02":"8600000","Hour03":"8400000"}'),
  ('DemaCome',       'Sistema', 'Sistema', DATE '2024-03-01',
   '{"Hour01":"8700000","Hour02":"8500000","Hour03":"8300000"}'),
  ('Gene',           'Sistema', 'Sistema', DATE '2024-03-01',
   '{"Hour01":"8900000","Hour02":"8700000","Hour03":"8500000"}'),
  ('PrecOferDesp',   'Recurso', 'PLNT1',   DATE '2024-03-01',
   '{"Hour01":"120.50","Hour02":"121.00","Hour03":""}'),
  ('EmisionesCO2Eq', 'Recurso', 'PLNT1',   DATE '2024-03-01',
   '{"Hour01":"0.00003","Hour02":"0.00004","Hour03":"0.00002"}'),
  ('PrecOferDesp',   'Recurso', 'PLNT2',   DATE '2024-03-01',
   '{"Hour01":"210.00","Hour02":"209.50","Hour03":"208.00"}'),
  ('EmisionesCO2Eq', 'Recurso', 'PLNT2',   DATE '2024-03-01',
   '{"Hour01":"0.00010","Hour02":"0.00011","Hour03":"0.00009"}');

INSERT INTO raw.load_audit (series_key, partition, rows_loaded, source_rows) VALUES
  ('precbolsnaci__sistema', DATE '2024-03-01', 1, 1);
