import boto3
import os

def lambda_handler(event, context):
    elbv2 = boto3.client('elbv2')
    asg = boto3.client('autoscaling')
    rds = boto3.client('rds')
    ssm = boto3.client('ssm')
    ec2 = boto3.client('ec2')
    
    # Se debe configurar previamente las Variables de Entorno
    NAT_INSTANCE_ID = os.environ['NAT_INSTANCE_ID']
    VPC_ID = os.environ['VPC_ID']
    SUBNET_IDS = os.environ['SUBNET_IDS'].split(',')
    SG_ID = os.environ['SG_ID']
    ASG_NAME = os.environ['ASG_NAME']
    DB_ID = os.environ['DB_ID']
    
    
    print("Iniciando rutina de encendido FinOps...")

    # 0. Encender NAT tempranamente
    print("Enviando señal de encendido a la NAT Instance...")
    try:
        ec2.start_instances(InstanceIds=[NAT_INSTANCE_ID])
    except Exception as e:
        print(f"Error al iniciar NAT: {str(e)}")

    # 1. Iniciar RDS
    try:
        print("Iniciando base de datos RDS...")
        rds.start_db_instance(DBInstanceIdentifier=DB_ID)
    except Exception as e:
        print("El RDS ya está en ejecución o procesando:", str(e))

    # 2. Crear Target Group
    print("Creando Target Group...")
    tg_res = elbv2.create_target_group(
        Name='TechNova-TG-WebServers',
        Protocol='HTTP', 
        Port=80, 
        VpcId=VPC_ID,
        TargetType='instance',
        HealthCheckPath='/000mx/_init/init.php'
    )
    tg_arn = tg_res['TargetGroups'][0]['TargetGroupArn']

    # 3. Crear ALB
    print("Creando ALB...")
    alb_res = elbv2.create_load_balancer(
        Name='TechNova-ALB',
        Subnets=SUBNET_IDS, 
        SecurityGroups=[SG_ID],
        Scheme='internet-facing', 
        IpAddressType='ipv4'
    )
    alb_arn = alb_res['LoadBalancers'][0]['LoadBalancerArn']
    alb_dns = alb_res['LoadBalancers'][0]['DNSName']

    # 4. Crear Listener
    print("Creando Listener (Puerto 80)...")
    elbv2.create_listener(
        LoadBalancerArn=alb_arn, 
        Protocol='HTTP', 
        Port=80,
        DefaultActions=[{'Type': 'forward', 'TargetGroupArn': tg_arn}]
    )

    # 5. Limpiar ASG antes de conectar
    print("Verificando que el ASG esté limpio...")
    try:
        asg_info = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[ASG_NAME])
        tgs_viejos = asg_info['AutoScalingGroups'][0].get('TargetGroupARNs', [])
        if tgs_viejos:
            asg.detach_load_balancer_target_groups(AutoScalingGroupName=ASG_NAME, TargetGroupARNs=tgs_viejos)
    except Exception as e:
        print(f"Error en validacion de limpieza: {str(e)}")

    # 6. Actualizar ASG
    print("Conectando el NUEVO Target Group al ASG...")
    asg.attach_load_balancer_target_groups(AutoScalingGroupName=ASG_NAME, TargetGroupARNs=[tg_arn])
    
    print("Esperando confirmación de red: Verificando que la NAT Instance esté 'running'...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[NAT_INSTANCE_ID])
    print("NAT Instance operativa. La red está lista.")

    print("Escalando ASG...")
    asg.update_auto_scaling_group(AutoScalingGroupName=ASG_NAME, MinSize=1, MaxSize=4, DesiredCapacity=1)

    # 7. Guardar nuevo DNS en Parameter Store
    print(f"Guardando nuevo DNS en Parameter Store: {alb_dns}")
    ssm.put_parameter(
        Name='/technova/alb/dns',
        Description='Enlace actualizado dinámicamente por Lambda',
        Value=alb_dns, 
        Type='String', 
        Overwrite=True
    )

    return {'status': 'Éxito: Infraestructura recreada', 'Nuevo_DNS': alb_dns}