use tungstenite::{connect, Message};
use url::Url;


static BINANCE_WS_API: &str = "wss://stream.binance.com:9443";
// ethbtc@depth5@100ms
fn main() {
    let binance_url = format!("{}/ws", BINANCE_WS_API);
    let (mut socket, response) =
        connect(Url::parse(&binance_url).unwrap()).expect("Can't connect.");
    println!("Connected to binance stream.");
    println!("HTTP status code: {}", response.status());
    println!("Response headers:");
    for (ref header, ref header_value) in response.headers() {
        println!("- {}: {:?}", header, header_value);
    }
	
	let msg = Message::Text("{\"method\": \"SUBSCRIBE\", \"params\": [ \"btcusdt@aggTrade\", \"btcusdt@depth\", \"ethusdt@aggTrade\", \"ethusdt@depth\", \"bnbusdt@aggTrade\", \"bnbusdt@depth\", \"dogeusdt@aggTrade\", \"dogeusdt@depth\"], \"id\": 1}".to_string());
    socket.write_message(msg).unwrap();
	
	loop {
        let msg = socket.read_message().expect("Error reading message");
        // let msg = match msg {
        //     tungstenite::Message::Text(s) => s,
        //     _ => {
        //         panic!("Error getting text");
        //     }
        // };
        // let parsed: models::DepthStreamData = serde_json::from_str(&msg).expect("Can't parse");
		println!("{}", msg);
	}
}