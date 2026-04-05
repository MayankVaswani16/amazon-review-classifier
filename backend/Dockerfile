FROM eclipse-temurin:17-jre-jammy

WORKDIR /app

# Install curl for health checks (not present in jre-jammy by default)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the locally compiled JAR file instead of building it inside Docker
# You must run 'mvn clean package -DskipTests' on your host machine first
COPY target/*.jar app.jar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["java", "-Xms256m", "-Xmx512m", "-jar", "app.jar"]

