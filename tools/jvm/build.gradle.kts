// tools/check_jvm.py 编译示例时用的依赖，版本要和章节头部的 versions 一致
plugins { java }

repositories {
    mavenCentral()
    google()
}

dependencies {
    implementation(platform("org.springframework.boot:spring-boot-dependencies:4.1.2"))
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-webflux")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-test")
    implementation("org.springframework.boot:spring-boot-webmvc-test")
    implementation("org.springframework.security:spring-security-core")
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("org.flywaydb:flyway-core:13.12.0")
    implementation("org.xerial:sqlite-jdbc:3.50.3.0")
    implementation("com.openai:openai-java:4.95.0")
    implementation("dev.langchain4j:langchain4j:1.23.0")
    implementation("dev.langchain4j:langchain4j-open-ai:1.23.0")
    implementation("io.modelcontextprotocol.sdk:mcp:2.1.0")
    implementation("com.squareup.retrofit2:retrofit:3.0.0")
    implementation("com.squareup.okhttp3:okhttp-jvm:5.5.1")
    implementation("com.squareup.okhttp3:okhttp-sse:5.5.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor:1.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.9.0")
    implementation("org.jetbrains.kotlin:kotlin-test-junit5:2.4.0")
    implementation("io.mockk:mockk:1.14.9")
    implementation("androidx.room:room-runtime-jvm:2.8.4")
    implementation("com.google.dagger:dagger:2.59")
}

tasks.register("classpath") {
    doLast { file("classpath.txt").writeText(configurations.compileClasspath.get().asPath) }
}
