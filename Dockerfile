# Lightweight multi-stage production Dockerfile for Google Cloud Run (Node.js 22)
FROM node:22-slim AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy application source code and assets
COPY tsconfig.json ./
COPY src ./src
COPY server.ts ./
COPY public ./public
COPY assets ./assets
COPY architecture.html ./

# Build TypeScript
RUN npm run build

# Production runner image
FROM node:22-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=8080

# Install production dependencies only
COPY package*.json ./
RUN npm ci --omit=dev

# Copy compiled files and static assets
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/public ./public
COPY --from=builder /app/assets ./assets
COPY --from=builder /app/architecture.html ./architecture.html

# Run as non-root user for security best practices
USER node

# Expose default Cloud Run port
EXPOSE 8080

# Run Cloud Run HTTP server using Node.js
CMD ["node", "dist/server.js"]
