import jwt from 'jsonwebtoken';

const ACCESS_TOKEN_SECRET = process.env.ACCESS_TOKEN_SECRET || 'default_secret';

export const handler = async (event) => {
    console.log("Received event:", JSON.stringify(event, null, 2));

    try {
        // Extract Authorization header
        const authHeader = event.authorizationToken;
        if (!authHeader) {
            console.error("No Authorization header provided.");
            return generatePolicy('user', 'Deny', event.methodArn);
        }

        // Extract JWT token from header
        const token = authHeader.replace('Bearer ', '');
        console.log("Token extracted:", token);

        // Verify JWT
        const decoded = jwt.verify(token, ACCESS_TOKEN_SECRET);
        console.log("Token is valid:", decoded);

        return generatePolicy(decoded.sub, 'Allow', event.methodArn, decoded);
    } catch (error) {
        console.error("Token validation failed:", error.message);
        return generatePolicy('user', 'Deny', event.methodArn);
    }
};

// Function to generate API Gateway policies
const generatePolicy = (principalId, effect, resource, context) => {
    const authResponse = {
        principalId,
        policyDocument: {
            Version: '2012-10-17',
            Statement: [
                {
                    Effect: effect,
                    Action: 'execute-api:Invoke',
                    Resource: resource,
                },
            ],
        },
    };

    if (context) {
        authResponse.context = { user: JSON.stringify(context) };
    }

    return authResponse;
};
