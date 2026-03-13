/*
 * T Hardware Protocol — Arduino Sketch
 * Flash once. T handles the rest.
 *
 * Protocol (newline-terminated commands over Serial):
 *   PING                  → PONG
 *   DWRITE <pin> <HIGH|LOW>  → OK <pin> <HIGH|LOW>
 *   DREAD <pin>           → OK <pin> <HIGH|LOW>
 *   AREAD <pin>           → OK <pin> <value 0-1023>
 *   DHT <pin>             → OK <temp_C> <humidity_%>
 *   PWM <pin> <0-255>     → OK <pin> <value>
 *
 * DHT sensor: uncomment DHT library include below and set DHT_TYPE.
 * Baud rate: 9600 (T auto-detects).
 */

// ── Optional: DHT sensor support ────────────────────────────────────────────
// Requires DHT sensor library: Sketch → Include Library → DHT sensor library
// #include <DHT.h>
// #define DHT_TYPE DHT22   // or DHT11

#define BAUD_RATE 9600
#define CMD_MAX   64

char    cmd_buf[CMD_MAX];
uint8_t cmd_pos = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial);   // wait for USB serial on Leonardo/Micro
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmd_pos > 0) {
        cmd_buf[cmd_pos] = '\0';
        handle_command(cmd_buf);
        cmd_pos = 0;
      }
    } else if (cmd_pos < CMD_MAX - 1) {
      cmd_buf[cmd_pos++] = c;
    }
  }
}

void handle_command(const char* cmd) {
  char verb[16] = {0};
  sscanf(cmd, "%15s", verb);

  // ── PING ──────────────────────────────────────────────────────────────────
  if (strcmp(verb, "PING") == 0) {
    Serial.println("PONG");
    return;
  }

  // ── DWRITE <pin> <HIGH|LOW> ───────────────────────────────────────────────
  if (strcmp(verb, "DWRITE") == 0) {
    int  pin;
    char state[8] = {0};
    if (sscanf(cmd + 7, "%d %7s", &pin, state) == 2) {
      pinMode(pin, OUTPUT);
      bool high = (strcmp(state, "HIGH") == 0 || strcmp(state, "1") == 0);
      digitalWrite(pin, high ? HIGH : LOW);
      Serial.print("OK ");
      Serial.print(pin);
      Serial.print(" ");
      Serial.println(high ? "HIGH" : "LOW");
    } else {
      Serial.println("ERR bad DWRITE args");
    }
    return;
  }

  // ── DREAD <pin> ───────────────────────────────────────────────────────────
  if (strcmp(verb, "DREAD") == 0) {
    int pin;
    if (sscanf(cmd + 6, "%d", &pin) == 1) {
      pinMode(pin, INPUT);
      int val = digitalRead(pin);
      Serial.print("OK ");
      Serial.print(pin);
      Serial.println(val == HIGH ? " HIGH" : " LOW");
    } else {
      Serial.println("ERR bad DREAD args");
    }
    return;
  }

  // ── AREAD <pin> ───────────────────────────────────────────────────────────
  if (strcmp(verb, "AREAD") == 0) {
    char pin_str[8] = {0};
    sscanf(cmd + 6, "%7s", pin_str);
    // Convert A0-A5 to analog pin numbers
    int pin = -1;
    if (pin_str[0] == 'A' || pin_str[0] == 'a') {
      pin = A0 + atoi(pin_str + 1);
    } else {
      pin = atoi(pin_str);
    }
    if (pin >= 0) {
      int val = analogRead(pin);
      Serial.print("OK ");
      Serial.print(pin_str);
      Serial.print(" ");
      Serial.println(val);
    } else {
      Serial.println("ERR bad AREAD args");
    }
    return;
  }

  // ── PWM <pin> <0-255> ─────────────────────────────────────────────────────
  if (strcmp(verb, "PWM") == 0) {
    int pin, value;
    if (sscanf(cmd + 4, "%d %d", &pin, &value) == 2) {
      value = constrain(value, 0, 255);
      analogWrite(pin, value);
      Serial.print("OK ");
      Serial.print(pin);
      Serial.print(" ");
      Serial.println(value);
    } else {
      Serial.println("ERR bad PWM args");
    }
    return;
  }

  // ── DHT <pin> ─────────────────────────────────────────────────────────────
  if (strcmp(verb, "DHT") == 0) {
    int pin;
    if (sscanf(cmd + 4, "%d", &pin) == 1) {
      // Uncomment the DHT block below when DHT library is installed:
      /*
      DHT dht(pin, DHT_TYPE);
      dht.begin();
      float temp = dht.readTemperature();
      float hum  = dht.readHumidity();
      if (isnan(temp) || isnan(hum)) {
        Serial.println("ERR DHT read failed");
      } else {
        Serial.print("OK ");
        Serial.print(temp, 1);
        Serial.print(" ");
        Serial.println(hum, 1);
      }
      */
      Serial.println("ERR DHT library not enabled — uncomment in sketch");
    } else {
      Serial.println("ERR bad DHT args");
    }
    return;
  }

  Serial.print("ERR unknown command: ");
  Serial.println(verb);
}
