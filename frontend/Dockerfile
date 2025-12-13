# Frontend Dockerfile for Arivu Application
# Multi-stage build: Build stage + Nginx production stage

FROM node:lts-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json yarn.lock* ./

# Install dependencies with Yarn
RUN yarn install --frozen-lockfile --production=false

# Copy application code
COPY . .

# Build argument for backend URL
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

# Build the React application
RUN yarn build

# Production stage with Nginx
FROM nginx:1.25-alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Create nginx cache directories
RUN mkdir -p /var/cache/nginx/client_temp && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
