import * as cdk from 'aws-cdk-lib';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import { Construct } from 'constructs';


export class WAFStack extends cdk.Stack {
 public readonly webAclArn: string;


 constructor(scope: Construct, id: string, props?: cdk.StackProps) {
   super(scope, id, props);


   // WAF Web ACL with rate limiting (must be in us-east-1 for CloudFront)
   const webAcl = new wafv2.CfnWebACL(this, 'ClaimsWebACL', {
     scope: 'CLOUDFRONT',
     defaultAction: { allow: {} },
     rules: [
       {
         name: 'RateLimitRule',
         priority: 1,
         statement: {
           rateBasedStatement: {
             limit: 500,
             evaluationWindowSec: 60,
             aggregateKeyType: 'IP'
           }
         },
         action: { block: {} },
         visibilityConfig: {
           sampledRequestsEnabled: true,
           cloudWatchMetricsEnabled: true,
           metricName: 'RateLimitRule'
         }
       }
     ],
     visibilityConfig: {
       sampledRequestsEnabled: true,
       cloudWatchMetricsEnabled: true,
       metricName: 'ClaimsWebACL'
     }
   });


   this.webAclArn = webAcl.attrArn;


   new cdk.CfnOutput(this, 'WAFWebACLArn', {
     value: webAcl.attrArn,
     description: 'WAF Web ACL ARN with rate limiting',
     exportName: `${this.stackName}-WebACLArn`
   });
 }
}
