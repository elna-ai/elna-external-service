import AWS from 'aws-sdk';
import crypto from 'crypto';
import jwt from 'jsonwebtoken';
import { serialize } from 'cookie';
import bs58 from 'bs58';
import nacl from 'tweetnacl';

AWS.config.update({ region: 'us-east-1' });
const dynamoDB = new AWS.DynamoDB.DocumentClient();

const TABLE_NAME = process.env.USER_TABLE || "Users";
const ACCESS_TOKEN_SECRET = process.env.ACCESS_TOKEN_SECRET || "default_secret";
// const REFRESH_TOKEN_SECRET = process.env.REFRESH_TOKEN_SECRET || "default_refresh_secret";
const iv = process.env.IV;
const gmtype = process.env.GM_TYPE;
const algorithm = 'aes-256-cbc';

// Helper function to encode the public key for JWT
const encodePublicKey = (publicKey) => {
    return ACCESS_TOKEN_SECRET + publicKey.substring(0, 8);
};

const parseJSON = (body) => {
    try {
        return JSON.parse(body);
    } catch (error) {
        console.error("Error parsing JSON:", error);
        return null;
    }
};

export const handler = async (event) => {
    console.log("Received event:", JSON.stringify(event, null, 2));

    try {
        // Extract request details from the event
        let httpMethod, path, body, headers, cookies = {};
        
        // Handle different event formats (direct Lambda invocation vs API Gateway)
        if (event.httpMethod && event.path) {
            // API Gateway format
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
            // Parse cookies
            if (headers.cookie || headers.Cookie) {
                const cookieStr = headers.cookie || headers.Cookie;
                cookies = cookieStr.split(';').reduce((acc, cookie) => {
                    const [key, value] = cookie.trim().split('=');
                    acc[key] = value;
                    return acc;
                }, {});
            }
        } else if (event.requestContext && event.requestContext.http) {
            // HTTP API format
            httpMethod = event.requestContext.http.method;
            path = event.requestContext.http.path;
            body = event.body;
            headers = event.headers || {};
            // Parse cookies
            if (headers.cookie || headers.Cookie) {
                const cookieStr = headers.cookie || headers.Cookie;
                cookies = cookieStr.split(';').reduce((acc, cookie) => {
                    const [key, value] = cookie.trim().split('=');
                    acc[key] = value;
                    return acc;
                }, {});
            }
        } else {
            // Direct invocation format
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
            // Parse cookies
            if (headers.cookie || headers.Cookie) {
                const cookieStr = headers.cookie || headers.Cookie;
                cookies = cookieStr.split(';').reduce((acc, cookie) => {
                    const [key, value] = cookie.trim().split('=');
                    acc[key] = value;
                    return acc;
                }, {});
            }
        }
        
        console.log(`Processing ${httpMethod} ${path}`);
        
        const parsedBody = parseJSON(body);

        if (!parsedBody && httpMethod === "POST") {
            console.error("Invalid JSON body received:", body);
            return { 
                statusCode: 400, 
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ error: "Invalid JSON body" }) 
            };
        }

        // Create context object to simulate the context from the original code
        const context = {
            req: {
                cookies: cookies
            },
            res: {
                status: (statusCode) => ({
                    json: (data) => ({
                        statusCode,
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(data)
                    })
                })
            }
        };

        // Route the request to the appropriate handler
        if (httpMethod === "POST" && path === "/tokens") {
            return await generateTokens(parsedBody, context);
        } else if (httpMethod === "POST" && path === "/nonce") {
            return await createNonce(parsedBody, context);
        } else if (httpMethod === "POST" && path === "/refresh") {
            return await refreshToken(context);
        } else if (httpMethod === "GET" && path === "/user") {
            return await getUser(headers);
        } else {
            return { 
                statusCode: 400, 
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ error: "Invalid request path or method" }) 
            };
        }
    } catch (error) {
        console.error("Lambda Function Error:", error);
        return { 
            statusCode: 500, 
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ 
                error: "Internal server error", 
                message: error.message || String(error)
            }) 
        };
    }
};

async function createNonce(requestBody, context) {
    try {
        const { publicKey } = requestBody;
        
        if (!publicKey) {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Missing publicKey" }) 
            };
        }
        
        const nonce = crypto.randomBytes(32).toString("base64");
        const currentTime = Date.now();
        
        // Ensure IV and gmtype are available
        if (!iv || !gmtype) {
            console.warn("Missing IV or gmtype environment variables, using default values");
            // Generate a response without encryption
            await dynamoDB.put({
                TableName: TABLE_NAME,
                Item: {
                    publicKey: publicKey,
                    nonce: nonce,
                    createdAt: currentTime,
                    updatedAt: currentTime,
                }
            }).promise();
            
            return { 
                statusCode: 200,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nonce }) 
            };
        }
        
        const ivBuffer = Buffer.from(iv, "base64");
        const gmtypeBuffer = Buffer.from(gmtype, "base64");
        const cipher = crypto.createCipheriv(algorithm, gmtypeBuffer, ivBuffer);

        const dataToEncrypt = `${nonce}:${currentTime}`;

        let encrypted = cipher.update(dataToEncrypt, "utf8", "hex");
        encrypted += cipher.final("hex");

        await dynamoDB.put({
            TableName: TABLE_NAME,
            Item: {
                publicKey: publicKey,
                nonce: nonce,
                createdAt: currentTime,
                updatedAt: currentTime,
            }
        }).promise();

        // Return response with cookie
        return {
            statusCode: 200,
            headers: {
                "Set-Cookie": serialize("auth-nonce", encrypted, {
                    httpOnly: true,
                    sameSite: "None",
                    path: "/",
                    secure: true,
                    maxAge: 120,
                }),
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ nonce })
        };
    } catch (error) {
        console.error("Error creating nonce:", error);
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                error: "Failed to create nonce", 
                message: error.message 
            }) 
        };
    }
}

async function generateTokens(requestBody, context) {
    try {
        const { publicKey, signature, nonce, isoTimestamp } = requestBody;

        if (!publicKey || !signature || !nonce || !isoTimestamp) {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Missing required parameters (publicKey, signature, nonce, isoTimestamp)" }) 
            };
        }

        const ivBuffer = Buffer.from(iv, "base64");
        const gmtypeBuffer = Buffer.from(gmtype, "base64");
        
        // Get the encrypted nonce from cookies
        const enNonce = context.req.cookies['auth-nonce'];
        console.log("enNonce", enNonce);

        if (!enNonce) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Nonce not found in cookies" }) 
            };
        }

        // Decrypt and validate the nonce
        const decipher = crypto.createDecipheriv(algorithm, gmtypeBuffer, ivBuffer);
        let decrypted = decipher.update(enNonce, "hex", "utf8");
        decrypted += decipher.final("utf8");
        
        const [decNonce, timestamp] = decrypted.split(":");
        console.log("decNonce", decNonce);
        
        // Get the current time in milliseconds
        const currentTime = new Date().getTime();
        // Calculate the timestamp 4 minutes ago (same as in verifyWalletSignature)
        const fourMinutesAgo = currentTime - 4 * 60 * 1000;

        if (decNonce !== nonce || timestamp < fourMinutesAgo) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid or expired nonce" }) 
            };
        }

        // Create the message to verify (same format as in the original code)
        const message = `
Welcome to DeFi agent!

Please sign this message to authenticate your wallet and log in.

- Nonce: ${nonce}
- Solana account: ${publicKey}
- Issued at: ${isoTimestamp}

Signing is the only way that you are the owner of the wallet you are connecting. Signing is safe, gas-less transaction that does not in any way give DeFi agnet permission to perform any transaction with your wallet.
`;

        // Verify the signature
        const messageBytes = new TextEncoder().encode(message);
        const publicKeyBytes = bs58.decode(publicKey);
        const signatureBytes = bs58.decode(signature);

        const isValid = nacl.sign.detached.verify(messageBytes, signatureBytes, publicKeyBytes);

        if (!isValid) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Signature verification failed" }) 
            };
        }

        // Generate tokens
        const accessToken = jwt.sign({ sub: publicKey }, encodePublicKey(publicKey), { expiresIn: "7d" });
        const refreshToken = jwt.sign({ sub: publicKey }, encodePublicKey(publicKey), { expiresIn: "30d" });

        // Store user data in DynamoDB
        await dynamoDB.put({
            TableName: TABLE_NAME,
            Item: {
                publicKey: publicKey,
                refreshToken: refreshToken,
                updatedAt: Date.now(),
            }
        }).promise();

        console.log("✅ Tokens generated for user:", publicKey);

        return {
            statusCode: 200,
            headers: {
                "Set-Cookie": serialize("refresh-token", refreshToken, {
                    httpOnly: true,
                    secure: true,
                    sameSite: "None",
                    path: "/",
                    maxAge: 30 * 24 * 60 * 60, // 30 days
                }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ accessToken })
        };
    } catch (error) {
        console.error("❌ Error generating tokens:", error);
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                error: "Failed to generate tokens", 
                message: error.message 
            }) 
        };
    }
}

async function refreshToken(context) {
    try {
        // Get refresh token from cookies
        const refreshToken = context.req.cookies['refresh-token'];
        
        if (!refreshToken) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Refresh token not found" }) 
            };
        }

        // Decode the token to get the public key
        const decodedToken = jwt.decode(refreshToken);
        if (!decodedToken || !decodedToken.sub) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid refresh token format" }) 
            };
        }

        const publicKey = decodedToken.sub;
        const encodedKey = encodePublicKey(publicKey);
        
        try {
            // Verify the refresh token
            jwt.verify(refreshToken, encodedKey);
            
            // Generate new tokens
            const newAccessToken = jwt.sign({ sub: publicKey }, encodedKey, { expiresIn: "7d" });
            const newRefreshToken = jwt.sign({ sub: publicKey }, encodedKey, { expiresIn: "30d" });
            
            // Update token in DynamoDB
            await dynamoDB.update({
                TableName: TABLE_NAME,
                Key: { publicKey },
                UpdateExpression: "SET refreshToken = :refreshToken, updatedAt = :updatedAt",
                ExpressionAttributeValues: {
                    ":refreshToken": newRefreshToken,
                    ":updatedAt": Date.now(),
                }
            }).promise();
            
            return {
                statusCode: 200,
                headers: {
                    "Set-Cookie": serialize("refresh-token", newRefreshToken, {
                        httpOnly: true,
                        secure: true,
                        sameSite: "None",
                        path: "/",
                        maxAge: 30 * 24 * 60 * 60, // 30 days
                    }),
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ accessToken: newAccessToken })
            };
        } catch (err) {
            console.error("❌ Error verifying refresh token:", err);
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    error: "Invalid or expired refresh token", 
                    message: err.message 
                }) 
            };
        }
    } catch (error) {
        console.error("❌ Error refreshing token:", error);
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                error: "Failed to refresh token", 
                message: error.message 
            }) 
        };
    }
}

async function getUser(headers) {
    console.log("🔍 Received headers:", headers);

    // Check various header formats for the authorization token
    const authHeader = headers.authorizationToken || headers.Authorization || headers.authorization;
    if (!authHeader) {
        console.error("❌ No Authorization header provided");
        return { 
            statusCode: 401, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Unauthorized: No token provided" }) 
        };
    }

    // Extract the token from the header
    const token = authHeader.replace("Bearer ", "");
    console.log("🔑 Extracted token:", token);

    try {
        // Decode the token to get the public key
        const decoded = jwt.decode(token);
        if (!decoded || !decoded.sub) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid token format" }) 
            };
        }

        const publicKey = decoded.sub;
        const encodedKey = encodePublicKey(publicKey);

        // Verify the token
        jwt.verify(token, encodedKey);
        console.log("✅ Token is valid:", decoded);

        // Fetch user data from DynamoDB
        const result = await dynamoDB.get({
            TableName: TABLE_NAME,
            Key: { publicKey },
        }).promise();

        if (!result.Item) {
            console.error("❌ User not found in database");
            return { 
                statusCode: 404, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "User not found" }) 
            };
        }

        // Return user data (excluding sensitive info)
        const userData = {
            publicKey: result.Item.publicKey,
            createdAt: result.Item.createdAt,
            updatedAt: result.Item.updatedAt,
        };

        console.log("✅ User retrieved:", userData);
        return { 
            statusCode: 200, 
            headers: { 
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,OPTIONS"
            },
            body: JSON.stringify(userData) 
        };
    } catch (error) {
        console.error("❌ Token validation failed:", error.message);
        return { 
            statusCode: 401, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                error: "Unauthorized: Invalid token", 
                message: error.message 
            }) 
        };
    }
}