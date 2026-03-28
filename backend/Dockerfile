# Multi-stage build for Spring Boot

# Stage 1: Build
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

# Stage 2: Run
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

# Install curl for health checks (not present in jre-jammy by default)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /app/target/*.jar app.jar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["java", "-Xms256m", "-Xmx512m", "-jar", "app.jar"]

