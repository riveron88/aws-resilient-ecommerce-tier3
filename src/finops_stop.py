import boto3
import time
import os

def lambda_handler(event, context):
    elbv2 = boto3.client('elbv2')
    asg = boto3.client('autoscaling')
    rds = boto3.client('rds')
    ec2 = boto3.client('ec2')
    
    # Configuracion previa de Variables de Entorno. 
    NAT_INSTANCE_ID = os.environ['NAT_INSTANCE_ID'] 
    ASG_NAME = os.environ['ASG_NAME']
    DB_ID = os.environ['DB_ID']

    print("Iniciando rutina de apagado FinOps...")

    # 1. Escalar ASG a 0
    print("Escalando ASG a 0...")
    asg.update_auto_scaling_group(AutoScalingGroupName=ASG_NAME, MinSize=0, MaxSize=0, DesiredCapacity=0)
    
    # 1.5 Limpieza de Target Groups Fantasma
    try:
        asg_info = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[ASG_NAME])
        tgs_pegados = asg_info['AutoScalingGroups'][0].get('TargetGroupARNs', [])
        
        if tgs_pegados:
            print(f"Desvinculando Target Groups antiguos del ASG: {tgs_pegados}")
            asg.detach_load_balancer_target_groups(AutoScalingGroupName=ASG_NAME, TargetGroupARNs=tgs_pegados)
            time.sleep(5)
    except Exception as e:
        print(f"Error al limpiar ASG: {str(e)}")

    # 2. Eliminar ALB
    try:
        albs = elbv2.describe_load_balancers(Names=['TechNova-ALB'])
        alb_arn = albs['LoadBalancers'][0]['LoadBalancerArn']
        print(f"Eliminando ALB: {alb_arn}...")
        elbv2.delete_load_balancer(LoadBalancerArn=alb_arn)
        time.sleep(15)
    except Exception as e:
        print("ALB no encontrado o ya eliminado.")

    # 3. Eliminar Target Group
    try:
        tgs = elbv2.describe_target_groups(Names=['TechNova-TG-WebServers'])
        tg_arn = tgs['TargetGroups'][0]['TargetGroupArn']
        print(f"Eliminando Target Group: {tg_arn}...")
        elbv2.delete_target_group(TargetGroupArn=tg_arn)
    except Exception as e:
        print("Target Group no encontrado o ya eliminado.")

    # 4. Detener RDS
    try:
        print("Deteniendo base de datos RDS...")
        rds.stop_db_instance(DBInstanceIdentifier=DB_ID)
    except Exception as e:
        print("El RDS ya está detenido o no se encontró:", str(e))
    
    # 5. Monitoreo de apagado del ASG y Apagado final de la NAT
    print("Verificando que las instancias EC2 del ASG se hayan terminado por completo...")
    while True:
        response = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[ASG_NAME])
        instances = response['AutoScalingGroups'][0]['Instances']
        
        if len(instances) == 0:
            print("Todas las instancias del ASG han sido terminadas exitosamente.")
            break 
        else:
            print(f"Esperando a que {len(instances)} instancias del ASG terminen (draining)...")
            time.sleep(15)
            
    print(f"Apagando NAT Instance para evitar costos nocturnos: {NAT_INSTANCE_ID}")
    ec2.stop_instances(InstanceIds=[NAT_INSTANCE_ID])

    return {'status': 'Éxito: Infraestructura eliminada y NAT detenida'}