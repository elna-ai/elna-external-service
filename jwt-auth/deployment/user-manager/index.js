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
const iv = process.env.IV;
const gmtype = process.env.GM_TYPE;
const algorithm = 'aes-256-cbc';

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
        let httpMethod, path, body, headers, cookies = {};
        
        if (event.httpMethod && event.path) {
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
        } else if (event.requestContext && event.requestContext.http) {
            httpMethod = event.requestContext.http.method;
            path = event.requestContext.http.path;
            body = event.body;
            headers = event.headers || {};
        } else {
            httpMethod = event.httpMethod;
            path = event.path;
            body = event.body;
            headers = event.headers || {};
        }

        if (headers.cookie || headers.Cookie) {
            const cookieStr = headers.cookie || headers.Cookie;
            cookies = cookieStr.split(';').reduce((acc, cookie) => {
                const [key, value] = cookie.trim().split('=');
                acc[key] = value;
                return acc;
            }, {});
        }

        console.log(`Processing ${httpMethod} ${path}`);
        
        const parsedBody = parseJSON(body);

        if (!parsedBody && httpMethod === "POST") {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid JSON body" }) 
            };
        }

        if (httpMethod === "POST" && path === "/tokens") {
            return await generateTokens(parsedBody, cookies);
        } else if (httpMethod === "POST" && path === "/nonce") {
            return await createNonce(parsedBody);
        } else if (httpMethod === "POST" && path === "/refresh") {
            return await refreshToken(cookies);
        } else if (httpMethod === "GET" && path === "/user") {
            return await getUser(headers);
        } else {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid request path or method" }) 
            };
        }
    } catch (error) {
        console.error("Lambda Function Error:", error);
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Internal server error", message: error.message }) 
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

        await dynamoDB.put({
            TableName: TABLE_NAME,
            Item: {
                publicKey: publicKey,
                nonce: nonce,
                createdAt: currentTime,
                updatedAt: currentTime,
            }
        }).promise();

        if (!iv || !gmtype) {
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
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Failed to create nonce", message: error.message }) 
        };
    }
}

async function generateTokens(requestBody, cookies) {
    try {
        const { publicKey, signature, nonce, isoTimestamp } = requestBody;
        if (!publicKey || !signature || !nonce || !isoTimestamp) {
            return { 
                statusCode: 400, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Missing required parameters" }) 
            };
        }

        const enNonce = cookies['auth-nonce'];
        if (!enNonce) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Nonce not found in cookies" }) 
            };
        }

        const ivBuffer = Buffer.from(iv, "base64");
        const gmtypeBuffer = Buffer.from(gmtype, "base64");
        const decipher = crypto.createDecipheriv(algorithm, gmtypeBuffer, ivBuffer);
        let decrypted = decipher.update(enNonce, "hex", "utf8");
        decrypted += decipher.final("utf8");
        
        const [decNonce, timestamp] = decrypted.split(":");
        const currentTime = new Date().getTime();
        const fourMinutesAgo = currentTime - 4 * 60 * 1000;

        if (decNonce !== nonce || timestamp < fourMinutesAgo) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid or expired nonce" }) 
            };
        }

        const message = `
Welcome to DeFi agent!

Please sign this message to authenticate your wallet and log in.

- Nonce: ${nonce}
- Solana account: ${publicKey}
- Issued at: ${isoTimestamp}

Signing is the only way that you are the owner of the wallet you are connecting. Signing is safe, gas-less transaction that does not in any way give DeFi agnet permission to perform any transaction with your wallet.
`;
        const messageBytes = new TextEncoder().encode(message);
        const publicKeyBytes = bs58.decode(publicKey);
        const signatureBytes = bs58.decode(signature);
        const isValid = nacl.sign.detached.verify(messageBytes, signatureBytes, publicKeyBytes);

        if (!isValid) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    error: "Signature verification failed"
                }) 
            };
        }

        const accessToken = jwt.sign({ sub: publicKey }, encodePublicKey(publicKey), { expiresIn: "7d" });
        const refreshToken = jwt.sign({ sub: publicKey }, encodePublicKey(publicKey), { expiresIn: "30d" });

        await dynamoDB.put({
            TableName: TABLE_NAME,
            Item: {
                publicKey: publicKey,
                refreshToken: refreshToken,
                updatedAt: Date.now(),
            }
        }).promise();

        return {
            statusCode: 200,
            headers: {
                "Set-Cookie": serialize("refresh-token", refreshToken, {
                    httpOnly: true,
                    secure: true,
                    sameSite: "None",
                    path: "/",
                    maxAge: 30 * 24 * 60 * 60,
                }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ accessToken })
        };
    } catch (error) {
        return { 
            statusCode: 500, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Failed to generate tokens", message: error.message }) 
        };
    }
}

async function refreshToken(cookies) {
    try {
        const refreshToken = cookies['refresh-token'];
        if (!refreshToken) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Refresh token not found" }) 
            };
        }

        const decodedToken = jwt.decode(refreshToken);
        if (!decodedToken?.sub) {
            return { 
                statusCode: 403, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid refresh token" }) 
            };
        }

        const publicKey = decodedToken.sub;
        const encodedKey = encodePublicKey(publicKey);
        
        jwt.verify(refreshToken, encodedKey);
        const newAccessToken = jwt.sign({ sub: publicKey }, encodedKey, { expiresIn: "7d" });
        const newRefreshToken = jwt.sign({ sub: publicKey }, encodedKey, { expiresIn: "30d" });

        await dynamoDB.update({
            TableName: TABLE_NAME,
            Key: { publicKey },
            UpdateExpression: "SET refreshToken = :rt, updatedAt = :ua",
            ExpressionAttributeValues: { ":rt": newRefreshToken, ":ua": Date.now() }
        }).promise();

        return {
            statusCode: 200,
            headers: {
                "Set-Cookie": serialize("refresh-token", newRefreshToken, {
                    httpOnly: true,
                    secure: true,
                    sameSite: "None",
                    path: "/",
                    maxAge: 30 * 24 * 60 * 60,
                }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ accessToken: newAccessToken })
        };
    } catch (error) {
        return { 
            statusCode: 403, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Invalid refresh token", message: error.message }) 
        };
    }
}

async function getUser(headers) {
    const authHeader = headers.authorization || headers.Authorization;
    if (!authHeader) {
        return { 
            statusCode: 401, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Authorization header missing" }) 
        };
    }

    try {
        const token = authHeader.replace("Bearer ", "");
        const decoded = jwt.decode(token);
        const publicKey = decoded?.sub;
        
        if (!publicKey) {
            return { 
                statusCode: 401, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "Invalid token format" }) 
            };
        }

        const result = await dynamoDB.get({
            TableName: TABLE_NAME,
            Key: { publicKey }
        }).promise();

        if (!result.Item) {
            return { 
                statusCode: 404, 
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ error: "User not found" }) 
            };
        }

        return { 
            statusCode: 200, 
            headers: { 
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,OPTIONS"
            },
            body: JSON.stringify({
                publicKey: result.Item.publicKey,
                createdAt: result.Item.createdAt,
                updatedAt: result.Item.updatedAt
            }) 
        };
    } catch (error) {
        return { 
            statusCode: 401, 
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Invalid token", message: error.message }) 
        };
    }
}
