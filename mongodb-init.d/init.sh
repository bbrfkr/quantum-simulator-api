set -e

mongo <<EOF
use $MONGO_INITDB_DATABASE
var user = {
    user: "$MONGO_DB_USERNAME",
    pwd: "$MONGO_DB_PASSWORD",
    roles: [
        {
            role: "dbOwner",
            db: "$MONGO_INITDB_DATABASE"
        }
    ]
};
db.createUser(user);

use $MONGO_TESTDB_DATABASE
var user = {
    user: "$MONGO_DB_USERNAME",
    pwd: "$MONGO_DB_PASSWORD",
    roles: [
        {
            role: "dbOwner",
            db: "$MONGO_TESTDB_DATABASE"
        }
    ]
};
db.createUser(user);

use test;
db.dropDatabase();
EOF
