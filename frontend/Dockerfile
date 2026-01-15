FROM oven/bun:latest as builder

WORKDIR /app
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM oven/bun:latest
WORKDIR /app

# Copy built app and dependencies
COPY --from=builder /app/build build/
COPY --from=builder /app/package.json .
COPY --from=builder /app/node_modules node_modules/
# Copy the custom server
COPY --from=builder /app/server server/

EXPOSE 3000
ENV NODE_ENV=production
ENV ORIGIN=http://localhost:3000

# Run the custom server
CMD [ "bun", "server/server.ts" ]
