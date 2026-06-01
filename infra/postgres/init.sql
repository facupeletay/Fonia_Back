-- Schemas
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS scoring;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS mlops;

-- Usuarios por servicio
CREATE USER identity_user  WITH PASSWORD 'identity_pass';
CREATE USER clinical_user  WITH PASSWORD 'clinical_pass';
CREATE USER scoring_user   WITH PASSWORD 'scoring_pass';
CREATE USER analytics_user WITH PASSWORD 'analytics_pass';
CREATE USER mlops_user     WITH PASSWORD 'mlops_pass';

-- Permisos: cada usuario solo ve su schema
GRANT USAGE  ON SCHEMA identity  TO identity_user;
GRANT CREATE ON SCHEMA identity  TO identity_user;

GRANT USAGE  ON SCHEMA clinical  TO clinical_user;
GRANT CREATE ON SCHEMA clinical  TO clinical_user;

GRANT USAGE  ON SCHEMA scoring   TO scoring_user;
GRANT CREATE ON SCHEMA scoring   TO scoring_user;

GRANT USAGE  ON SCHEMA analytics TO analytics_user;
GRANT CREATE ON SCHEMA analytics TO analytics_user;

GRANT USAGE  ON SCHEMA mlops     TO mlops_user;
GRANT CREATE ON SCHEMA mlops     TO mlops_user;