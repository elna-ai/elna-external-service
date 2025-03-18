import AWS from 'aws-sdk';
import crypto from 'crypto';
import jwt from 'jsonwebtoken';
import { serialize } from 'cookie';

AWS.config.update({ region: 'us-east-1' });
const dynamoDB = new AWS.DynamoDB.DocumentClient();

const TABLE_NAME = process.env.USER_TABLE || "Users";
const ACCESS_TOKEN_SECRET = process.env.ACCESS_TOKEN_SECRET || "default_secret";
const REFRESH_TOKEN_SECRET = process.env.REFRESH_TOKEN_SECRET || "default_refresh_secret";
const iv = process.env.IV;
const gmtype = process.env.GM_TYPE;
const algorithm = 'aes-256-cbc';

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
        let httpMethod, path, body, headers;
        
        // Handle different event formats (direct Lambda invocation vs API Gateway)
        if (event.httpMethod && event.path) {
            // API Gateway format
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
        } else if (event.requestContext && event.requestContext.http) {
            // HTTP API format
            httpMethod = event.requestContext.http.method;
            path = event.requestContext.http.path;
            body = event.body;
            headers = event.headers || {};
        } else {
            // Direct invocation format
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
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

        // Route the request to the appropriate handler
        if (httpMethod === "POST" && path === "/tokens") {
            return await generateTokens(parsedBody);
        } else if (httpMethod === "POST" && path === "/nonce") {
            return await createNonce(parsedBody);
        } else if (httpMethod === "POST" && path === "/refresh") {
            return await refreshToken(parsedBody);
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

async function createNonce(requestBody) {
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

async function generateTokens(requestBody) {
    try {
        const { publicKey } = requestBody;

        if (!publicKey) {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Missing publicKey" }) 
            };
        }
        
        const accessToken = jwt.sign({ sub: publicKey }, ACCESS_TOKEN_SECRET, { expiresIn: "14d" });
        const refreshToken = jwt.sign({ sub: publicKey }, REFRESH_TOKEN_SECRET, { expiresIn: "30d" });

        // Store in DynamoDB
        await dynamoDB.put({
            TableName: TABLE_NAME,
            Item: {
                publicKey: publicKey,
                refreshToken: refreshToken,
                updatedAt: Date.now(),
            }
        }).promise();

        console.log("✅ Tokens stored in DynamoDB for user:", publicKey);

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

async function refreshToken(requestBody) {
    try {
        const { refreshToken } = requestBody;

        if (!refreshToken) {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Missing refreshToken" }) 
            };
        }

        // Verify the token
        const decoded = jwt.verify(refreshToken, REFRESH_TOKEN_SECRET);
        console.log("Decoded refresh token:", decoded);

        // Fetch user data from DynamoDB
        const result = await dynamoDB.get({
            TableName: TABLE_NAME,
            Key: { publicKey: decoded.sub },
        }).promise();

        if (!result.Item || result.Item.refreshToken !== refreshToken) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid refresh token" }) 
            };
        }

        // Generate new tokens
        const newAccessToken = jwt.sign({ sub: decoded.sub }, ACCESS_TOKEN_SECRET, { expiresIn: "14d" });
        const newRefreshToken = jwt.sign({ sub: decoded.sub }, REFRESH_TOKEN_SECRET, { expiresIn: "30d" });

        // Update refreshToken in DynamoDB
        await dynamoDB.update({
            TableName: TABLE_NAME,
            Key: { publicKey: decoded.sub },
            UpdateExpression: "SET refreshToken = :refreshToken, updatedAt = :updatedAt",
            ExpressionAttributeValues: {
                ":refreshToken": newRefreshToken,
                ":updatedAt": Date.now(),
            }
        }).promise();

        console.log("Tokens refreshed successfully for user:", decoded.sub);

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
    } catch (error) {
        console.error("Refresh token validation failed:", error);
        return { 
            statusCode: 401, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                error: "Invalid or expired refresh token", 
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
        // Verify the token
        const decoded = jwt.verify(token, ACCESS_TOKEN_SECRET);
        console.log("✅ Token is valid:", decoded);

        // Fetch user data from DynamoDB
        const result = await dynamoDB.get({
            TableName: TABLE_NAME,
            Key: { publicKey: decoded.sub },
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