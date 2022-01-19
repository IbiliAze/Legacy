#!/bin/bash

install_docker() {
    echo "Installing Docker"
    sudo apt -y install curl
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo apt-add-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt update -y
    sudo apt install -y docker-ce
    sudo usermod -aG docker ${USER}
}
docker &&  echo "No need to install Docker" || install_docker 
sudo apt install -y docker-compose

USER=nodeconfiguser
PASSWORD=7FEFjsNUGQAC40LsdiQ8DA
EMAIL=ibili73@gmail.com
REGISTRY_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4)
REGISTRY_PORT=5000

create_cert() {
    mkdir certs/
    # Passphrase: cisco
    echo "[ req ]
    distinguished_name  = req_distinguished_name
    x509_extensions     = req_ext
    default_md          = sha256
    prompt              = no
    encrypt_key         = no

    [ req_distinguished_name ]
    countryName            = \"GB\"
    localityName           = \"London\"
    organizationName       = \"NodeConfig\"
    organizationalUnitName = \"NodeConfig-Docker-CA\"
    commonName             = \"$REGISTRY_IP\"
    emailAddress           = \"$EMAIL\"

    [ req_ext ]
    subjectAltName = @alt_names

    [alt_names]
    DNS = \"$REGISTRY_IP\"" > openssl.conf
    openssl req \
        -x509 -newkey rsa:4096 -days 365 -config openssl.conf \
        -keyout certs/domain.key -out certs/domain.crt
    openssl x509 -text -noout -in certs/domain.crt
}

create_htpass_user() {
    if [ htpasswd 2> /dev/null ]; then
        sudo apt install -y apache2-utils
    else
        else echo "htpasswd exists"
    fi
    mkdir auth
    htpasswd -Bbn ${USER} ${PASSWORD} > auth/htpasswd
}

create_priv_reg() {
    echo "---
    version: '3'
    services:
        docker-registry:
            image: registry:2
            container_name: docker-registry
            restart: always
            environment:
                REGISTRY_HTTP_TLS_CERTIFICATE: ./certs/domain.crt
                REGISTRY_HTTP_TLS_KEY: ./certs/domain.key
                REGISTRY_AUTH: htpasswd
                REGISTRY_AUTH_HTPASSWD_PATH: /auth/htpasswd
                REGISTRY_AUTH_HTPASSWD_REALM: Registry Realm
            ports:
                - 5000:5000
            volumes:
                - docker-registry-data:/var/lib/registry
                - ./certs:/certs
                - ./auth:/auth
        docker-registry-ui:
            image: konradkleine/docker-registry-frontend
            container_name: docker-registry-ui
            ports:
                - 443:443
            environment:
                ENV_DOCKER_REGISTRY_HOST: docker-registry
                ENV_DOCKER_REGISTRY_PORT: 5000
                ENV_USE_SSL: 1
            volumes:
                - ./certs/domain.crt:/etc/apache2/server.crt:ro
                - ./certs/domain.key:/etc/apache2/server.key:ro
    volumes:
        docker-registry-data: {}
    " > docker-compose.yml
    docker-compose down
    docker-compose up -d
    docker-compose ps
}

create_cert
create_htpass_user
create_priv_reg
