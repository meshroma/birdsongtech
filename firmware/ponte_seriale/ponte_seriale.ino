// birdsongtech - ponte seriale per la prova TEXTMSG della Heltec V4
// Scheda: XIAO_ESP32S3 - Strumenti > USB CDC On Boot: Enabled
//
// Tutto quello che arriva dalla USB della XIAO (monitor seriale del PC)
// esce su D6 (TX, GPIO43) verso la V4 GPIO47 (RX), e tutto quello che
// arriva dalla V4 GPIO48 (TX) su D7 (RX, GPIO44) torna al PC.
// Collegamenti per la prova: D6 -> GPIO47, D7 <- GPIO48, GND <-> GND.
// NON collegare il 3V3 durante la prova (la XIAO e' alimentata dalla USB).

const uint32_t BAUD_V4 = 38400;   // deve coincidere con serial.baud della V4

void setup() {
  Serial.begin(115200);                          // USB verso il PC
  Serial1.begin(BAUD_V4, SERIAL_8N1, D7, D6);    // RX = D7, TX = D6
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);               // LED spento (attivo basso)
  delay(1500);
  Serial.println("birdsongtech - ponte seriale XIAO <-> V4 a 38400 baud");
  Serial.println("Scrivi una riga, ad esempio: BS1 H TF01 90 4000 0");
}

void loop() {
  while (Serial.available()) {
    Serial1.write(Serial.read());
  }
  while (Serial1.available()) {
    digitalWrite(LED_BUILTIN, LOW);              // lampeggio a ogni dato ricevuto
    Serial.write(Serial1.read());
  }
  digitalWrite(LED_BUILTIN, HIGH);
}
