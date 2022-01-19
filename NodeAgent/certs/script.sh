#!/bin/bash


echo step 1
echo "Creating self-signed certificate for CA"
openssl req -x509 -newkey rsa:2048 -days 365 -keyout ca/ca-encryped-key.pem -out ca/ca-cert.pem \
    -subj "/C=UK/ST=London/O=NodeConfig/CN=nodeagent-ca/emailAddress=ibili73@gmail.com"

# Get the decryped version of the key
openssl pkey -in ca/ca-encryped-key.pem -out ca/ca-key.pem

# View the cert info in text (x.509) format
openssl x509 -in ca/ca-cert.pem -noout -text 



echo step 2
echo "Generating private keys & CSR's"
openssl req -newkey rsa:2048 -keyout server/server-encrypted-key.pem -out server/server-req.pem \
    -subj "/C=UK/ST=London/O=NodeConfig/CN=nodeagent-server/emailAddress=ibili73@gmail.com"

openssl req -newkey rsa:2048 -keyout client/client-encrypted-key.pem -out client/client-req.pem \
    -subj "/C=UK/ST=London/O=NodeConfig/CN=nodeagent-client/emailAddress=ibili73@gmail.com"

# Get the decryped version of the key
openssl pkey -in server/server-encrypted-key.pem -out server/server-key.pem
openssl pkey -in client/client-encrypted-key.pem -out client/client-key.pem



echo step 3
echo "Singing CSR & Creating certificates"
openssl x509 -req -in server/server-req.pem -CA ca/ca-cert.pem -CAkey ca/ca-key.pem \
    -CAcreateserial -out server/server-cert.pem

openssl x509 -req -in client/client-req.pem -CA ca/ca-cert.pem -CAkey ca/ca-key.pem \
    -CAcreateserial -out client/client-cert.pem
