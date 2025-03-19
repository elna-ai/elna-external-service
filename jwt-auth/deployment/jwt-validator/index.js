import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import dotenv from 'dotenv';

dotenv.config();

const ACCESS_TOKEN_SECRET = process.env.ACCESS_TOKEN_SECRET || 'default_secret';

// AES configuration for encryption
const algorithm = 'aes-256-cbc';
const iv = process.env.IV;
const gmtype = process.env.GM_TYPE;

const ivBuffer = Buffer.from(iv, 'base64');
const gmtypeBuffer = Buffer.from(gmtype, 'base64');

// Encrypt the publicKey using AES-256-CBC
export const encodePublicKey = (publicKey) => {
    const cipher = crypto.createCipheriv(algorithm, gmtypeBuffer, ivBuffer);
    let encrypted = cipher.update(publicKey, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
};

// Decrypt the publicKey using AES-256-CBC
export const decodePublicKey = (encryptedPublicKey) => {
    const decipher = crypto.createDecipheriv(algorithm, gmtypeBuffer, ivBuffer);
    let decrypted = decipher.update(encryptedPublicKey, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
};

// JWT Authentication Helper
export const authenticateJWT = (token) => {
    if (!token) {
        throw new Error('No token provided');
    }

    try {
        var decodedToken = jwt.decode(token);
        const encodedPublicKey = encodePublicKey(decodedToken.sub);
        const decoded = jwt.verify(token, encodedPublicKey);
        return decoded;  // Return user info if the token is valid
    } catch (err) {
        throw new Error('Invalid or expired token');
    }
};

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
        const decoded = authenticateJWT(token);
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
