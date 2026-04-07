import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { WAFStack } from './waf-stack';


export interface ClaimsProcessingStackProps extends cdk.StackProps {
 wafStackName?: string;
 wafStack?: WAFStack;
}


export class ClaimsProcessingStack extends cdk.Stack {
 constructor(scope: Construct, id: string, props: ClaimsProcessingStackProps) {
   super(scope, id, props);


   // Create a new VPC with proper internet connectivity
   const vpc = new ec2.Vpc(this, 'ClaimsVPC', {
     maxAzs: 2,
     natGateways: 0, // Use public subnets only to save cost
     subnetConfiguration: [
       {
         cidrMask: 24,
         name: 'Public',
         subnetType: ec2.SubnetType.PUBLIC,
       }
     ]
   });


   // DynamoDB Table for Claims
   const claimsTable = new dynamodb.Table(this, 'ClaimsTable', {
     tableName: 'Claims',
     partitionKey: { name: 'claim_id', type: dynamodb.AttributeType.STRING },
     billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
     removalPolicy: cdk.RemovalPolicy.RETAIN
   });


   // Add Global Secondary Index for evidence analysis tracking
   claimsTable.addGlobalSecondaryIndex({
     indexName: 'EvidenceAnalysisIndex',
     partitionKey: {
       name: 'analysis_status',
       type: dynamodb.AttributeType.STRING
     },
     sortKey: {
       name: 'updated_at',
       type: dynamodb.AttributeType.STRING
     }
   });


   // Create S3 bucket for evidence storage
   const evidenceBucket = new s3.Bucket(this, 'EvidenceBucket', {
     bucketName: `claims-evidence-${this.account}-${this.region}`,
     removalPolicy: cdk.RemovalPolicy.DESTROY,
     autoDeleteObjects: true,
     versioned: false,
     publicReadAccess: false,
     blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL
   });


   // Cross-region reference to WAF ARN
   const webAclArn = props.wafStack ? props.wafStack.webAclArn : cdk.Fn.importValue(`${props.wafStackName || 'ClaimsWAFStack'}-WebACLArn`);


   // ECS Cluster
   const cluster = new ecs.Cluster(this, 'ClaimsCluster', {
     vpc,
     enableFargateCapacityProviders: true
   });


   // Task Definition
   const taskDefinition = new ecs.FargateTaskDefinition(this, 'ClaimsTaskDef', {
     memoryLimitMiB: 1024,
     cpu: 512
   });


   // Add ECR permissions to execution role
   taskDefinition.executionRole?.addManagedPolicy(
     iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
   );


   // Add Bedrock, DynamoDB, and S3 permissions to task role
   taskDefinition.taskRole.attachInlinePolicy(new iam.Policy(this, 'BedrockDynamoS3Policy', {
     statements: [
       new iam.PolicyStatement({
         effect: iam.Effect.ALLOW,
         actions: [
           'bedrock:InvokeModel',
           'bedrock:InvokeModelWithResponseStream'
         ],
         resources: ['*']
       }),
       new iam.PolicyStatement({
         effect: iam.Effect.ALLOW,
         actions: [
           'dynamodb:GetItem',
           'dynamodb:PutItem',
           'dynamodb:UpdateItem',
           'dynamodb:DeleteItem',
           'dynamodb:Query',
           'dynamodb:Scan'
         ],
         resources: [claimsTable.tableArn, `${claimsTable.tableArn}/index/*`]
       }),
       new iam.PolicyStatement({
         effect: iam.Effect.ALLOW,
         actions: [
           's3:GetObject',
           's3:GetObjectVersion',
           's3:PutObject',
           's3:PutObjectTagging',
           's3:GetObjectTagging',
           's3:ListBucket'
         ],
         resources: [evidenceBucket.bucketArn, evidenceBucket.arnForObjects('*')]
       })
     ]
   }));


   // Container
   const container = taskDefinition.addContainer('ClaimsContainer', {
     image: ecs.ContainerImage.fromAsset('..'), // Build from cloud_deployment directory
     logging: ecs.LogDrivers.awsLogs({
       streamPrefix: 'claims-app',
       logRetention: logs.RetentionDays.ONE_WEEK
     }),
     environment: {
       AWS_DEFAULT_REGION: this.region,
       CLAIMS_TABLE_NAME: claimsTable.tableName,
       EVIDENCE_BUCKET_NAME: evidenceBucket.bucketName
     }
   });


   container.addPortMappings({
     containerPort: 8000,
     protocol: ecs.Protocol.TCP
   });


   // ECS Service in public subnets
   const service = new ecs.FargateService(this, 'ClaimsService', {
     cluster,
     taskDefinition,
     desiredCount: 1,
     assignPublicIp: true, // Need public IP for internet access to ECR
     vpcSubnets: {
       subnetType: ec2.SubnetType.PUBLIC
     },
     platformVersion: ecs.FargatePlatformVersion.LATEST
   });


   // Ensure ECS security group allows outbound HTTPS for ECR access
   service.connections.allowToAnyIpv4(ec2.Port.tcp(443), 'Allow HTTPS outbound for ECR access');


   // ALB Security Group - Allow only CloudFront
   const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
     vpc,
     description: 'Security group for ALB - CloudFront access only',
     allowAllOutbound: true
   });


   // Look up CloudFront prefix list dynamically (ID differs per region)
   const cloudfrontPrefixList = ec2.PrefixList.fromLookup(this, 'CloudFrontPrefixList', {
     prefixListName: 'com.amazonaws.global.cloudfront.origin-facing'
   });

   albSecurityGroup.addIngressRule(
     ec2.Peer.prefixList(cloudfrontPrefixList.prefixListId),
     ec2.Port.tcp(80),
     'Allow from CloudFront only'
   );


   // Application Load Balancer (Internet-facing)
   const alb = new elbv2.ApplicationLoadBalancer(this, 'ClaimsALB', {
     vpc,
     internetFacing: true,
     vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
     securityGroup: albSecurityGroup,
     loadBalancerName: 'claims-alb',
     ipAddressType: elbv2.IpAddressType.IPV4, // IPv4 only
   });


   // Target Group
   const targetGroup = new elbv2.ApplicationTargetGroup(this, 'ClaimsTargetGroup', {
     port: 8000,
     protocol: elbv2.ApplicationProtocol.HTTP,
     vpc,
     targetType: elbv2.TargetType.IP,
     healthCheck: {
       path: '/',
       healthyHttpCodes: '200',
       timeout: cdk.Duration.seconds(30),
       interval: cdk.Duration.seconds(60),
       healthyThresholdCount: 2,
       unhealthyThresholdCount: 5
     },
     // Extended timeouts for video analysis
     deregistrationDelay: cdk.Duration.seconds(30),
     targetGroupName: 'claims-targets'
   });


   // Secret header to verify requests come from CloudFront
   const customHeaderName = 'X-Origin-Verify';
   const customHeaderValue = `claims-${this.account}-${this.region}`;


   // Listener validates the custom header from CloudFront
   const listener = alb.addListener('ClaimsListener', {
     port: 80,
     defaultAction: elbv2.ListenerAction.fixedResponse(403, {
       contentType: 'text/plain',
       messageBody: 'Forbidden'
     })
   });

   listener.addAction('ForwardWithHeaderCheck', {
     priority: 1,
     conditions: [
       elbv2.ListenerCondition.httpHeader(customHeaderName, [customHeaderValue])
     ],
     action: elbv2.ListenerAction.forward([targetGroup])
   });


   // Configure ALB attributes for extended timeouts
   const cfnAlb = alb.node.defaultChild as elbv2.CfnLoadBalancer;
   cfnAlb.addPropertyOverride('LoadBalancerAttributes', [
     {
       Key: 'idle_timeout.timeout_seconds',
       Value: '900' // 15 minutes for video analysis
     },
     {
       Key: 'routing.http2.enabled',
       Value: 'true'
     }
   ]);


   // Connect service to target group
   service.attachToApplicationTargetGroup(targetGroup);


   // CloudFront Distribution
   const distribution = new cloudfront.Distribution(this, 'ClaimsDistribution', {
     defaultBehavior: {
       origin: new origins.LoadBalancerV2Origin(alb, {
         protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
         customHeaders: {
           [customHeaderName]: customHeaderValue
         }
       }),
       viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
       cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED, // For dynamic content
       originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
       allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL // Allow POST, PUT, DELETE, etc.
     },
     webAclId: webAclArn
   });


   // Outputs
   new cdk.CfnOutput(this, 'CloudFrontURL', {
     value: `https://${distribution.distributionDomainName}`,
     description: 'CloudFront URL for the Claims Processing App'
   });


   new cdk.CfnOutput(this, 'DynamoDBTableName', {
     value: claimsTable.tableName,
     description: 'DynamoDB table name for claims data'
   });


   new cdk.CfnOutput(this, 'EvidenceBucketName', {
     value: evidenceBucket.bucketName,
     description: 'S3 bucket name for evidence storage'
   });
 }
}
