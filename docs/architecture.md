flowchart TB

%% =====================================================
%% ESTILOS
%% =====================================================
classDef aws fill:#FF9900,stroke:#232F3E,color:#ffffff,stroke-width:2px,font-weight:bold;
classDef network fill:#F8F8F8,stroke:#FF9900,stroke-width:2px,stroke-dasharray: 5 5;
classDef public fill:#E8F5E9,stroke:#2E7D32,color:#1B1B1B,stroke-width:1.5px;
classDef privateApp fill:#FFF3E0,stroke:#E65100,color:#1B1B1B,stroke-width:1.5px;
classDef privateData fill:#FCE4EC,stroke:#C2185B,color:#1B1B1B,stroke-width:1.5px;
classDef management fill:#E3F2FD,stroke:#1565C0,color:#1B1B1B,stroke-width:1.5px;
classDef storage fill:#F3E5F5,stroke:#6A1B9A,color:#1B1B1B,stroke-width:1.5px;
classDef security fill:#ECEFF1,stroke:#5E35B1,color:#1B1B1B,stroke-width:1.5px,stroke-dasharray: 5 5;
classDef ops fill:#FCE4EC,stroke:#AD1457,color:#1B1B1B,stroke-width:1.5px;

%% =====================================================
%% USUARIOS
%% =====================================================
User((🌐 Usuarios))
Internet((🌍 Internet))

%% =====================================================
%% RESOLUCIÓN NUEVO LINK
%% =====================================================
subgraph LINK["RESOLUCIÓN DE NUEVO LINK"]

    APIGW["🔌 Amazon API Gateway<br/>REST API"]

    LambdaURL["⚡ AWS Lambda<br/>(Genera nuevo link)"]

    ParameterStore["📄 AWS Systems Manager<br/>Parameter Store<br/>(Guarda nuevo link)"]

    APIGW --> LambdaURL
    LambdaURL --> ParameterStore

end

%% =====================================================
%% AWS CLOUD
%% =====================================================
subgraph AWS["☁️ AWS CLOUD"]

    subgraph VPC["🌐 VPC - 10.0.0.0/16"]

        %% =========================================
        %% LOAD BALANCER
        %% =========================================
        ALB["⚖️ Application Load Balancer<br/>HTTP : 80"]

        %% =========================================
        %% PUBLIC SUBNET A
        %% =========================================
        subgraph PUBA["🟢 Public Subnet A<br/>10.0.1.0/24"]

            NATA["🛜 NAT Instance<br/>(Cost Optimized)"]

        end

        %% =========================================
        %% AZ A
        %% =========================================
        subgraph AZA["🏢 AZ A"]

            subgraph APPA["🟠 Private App Subnet A<br/>10.0.11.0/24"]

                ASGA["💻 Auto Scaling Group<br/><br/>Siempre al menos 1 On-Demand<br/>El resto Spot Instances"]

                ONDA["🟦 On-Demand"]
                SPOTA1["🟧 Spot"]
                SPOTA2["🟧 Spot"]
                SPOTA3["🟧 Spot"]

            end

            subgraph DATAA["🔴 Private Data Subnet A<br/>10.0.21.0/24"]

                RDSP[("🗄️ Amazon RDS MariaDB<br/>Primary (Multi-AZ)")]

                DBA["DB + Sesiones PHP<br/><br/>Allow 3306 from SG-WebServers"]

            end

        end

        %% =========================================
        %% AZ B
        %% =========================================
        subgraph AZB["🏢 AZ B"]

            subgraph APPB["🟠 Private App Subnet B<br/>10.0.12.0/24"]

                ASGB["💻 Auto Scaling Group<br/><br/>Siempre al menos 1 On-Demand<br/>El resto Spot Instances"]

                ONDB["🟦 On-Demand"]
                SPOTB1["🟧 Spot"]
                SPOTB2["🟧 Spot"]

            end

            subgraph DATAB["🔴 Private Data Subnet B<br/>10.0.22.0/24"]

                RDSS[("🗄️ Amazon RDS MariaDB<br/>Standby (Multi-AZ)")]

                DBB["DB + Sesiones PHP<br/><br/>Allow 3306 from SG-WebServers"]

            end

        end

        %% =========================================
        %% STORAGE
        %% =========================================
        EFS[("📁 Amazon EFS<br/>Almacenamiento Compartido<br/>(NFS)")]

    end

end

%% =====================================================
%% OPERACIONES
%% =====================================================
subgraph OPS["📊 OPERACIONES, OBSERVABILIDAD Y FINOPS"]

    CW["📈 Amazon CloudWatch<br/>Métricas & Alarmas"]

    SNS["📩 Amazon SNS<br/>Alertas"]

    EventBridge["🕒 Amazon EventBridge<br/>Programación (Cron)"]

    LambdaFinOps["⚡ AWS Lambda<br/>(FinOps)<br/>Start / Stop Resources"]

    RES["• EC2 Auto Scaling Groups<br/>• RDS MariaDB (Primary)<br/>• NAT Instance"]

    CW --> SNS
    EventBridge --> LambdaFinOps
    LambdaFinOps --> RES

end

%% =====================================================
%% SECURITY GROUPS
%% =====================================================
subgraph SG["🔐 ENCADENAMIENTO DE SECURITY GROUPS"]

    SGALB["SG-ALB<br/>Allow 80 from Internet"]

    SGWEB["SG-WebServers<br/>Allow only from SG-ALB"]

    SGDB["SG-Database<br/>Allow 3306 only<br/>from SG-WebServers"]

    SGALB --> SGWEB
    SGWEB --> SGDB

end

%% =====================================================
%% FLUJO PRINCIPAL
%% =====================================================
User --> Internet
Internet -->|HTTP 80| ALB

%% =====================================================
%% API GATEWAY RESOLUCIÓN
%% =====================================================
User -.-> APIGW
ParameterStore -.->|Nuevo link recuperado| ALB

%% =====================================================
%% ALB A ASG
%% =====================================================
ALB --> ASGA
ALB --> ASGB

%% =====================================================
%% BASE DE DATOS
%% =====================================================
ASGA -->|MySQL 3306| RDSP
ASGB -->|MySQL 3306| RDSP

RDSP ==>|Replicación Síncrona| RDSS

%% =====================================================
%% EFS
%% =====================================================
EFS <-.->|Montaje NFS| ASGA
EFS <-.->|Montaje NFS| ASGB

%% =====================================================
%% NAT INTERNET ACCESS
%% =====================================================
ASGA -.->|Salida a Internet vía NAT A| NATA
ASGB -.->|Salida a Internet vía NAT A| NATA

%% =====================================================
%% MONITOREO
%% =====================================================
ALB -.-> CW
ASGA -.-> CW
ASGB -.-> CW
RDSP -.-> CW

%% =====================================================
%% SECURITY ATTACHMENT
%% =====================================================
SGALB -. Attached .-> ALB
SGWEB -. Attached .-> ASGA
SGWEB -. Attached .-> ASGB
SGDB -. Attached .-> RDSP

%% =====================================================
%% ESTILOS
%% =====================================================
class AWS aws;
class VPC network;
class PUBA public;
class APPA,APPB privateApp;
class DATAA,DATAB privateData;
class EFS storage;
class SGALB,SGWEB,SGDB security;
class CW,SNS,EventBridge,LambdaFinOps ops;