//! Dump a serializer's fields + chosen decoders:
//! `cargo run --release --example dump_serializer -- <demo> <ClassName>`

use std::path::PathBuf;

use awpy::Parser;

fn main() {
    let mut args = std::env::args().skip(1);
    let path = PathBuf::from(args.next().expect("demo path"));
    let class = args.next().expect("class name");

    let parser = Parser::from_file(&path).expect("open");
    let sers = parser.parse_send_tables().expect("send tables");
    let ser = sers.get(&class).unwrap_or_else(|| {
        eprintln!("no serializer named {class}");
        std::process::exit(1);
    });

    println!("serializer {} — {} fields", ser.name, ser.fields.len());
    for (i, f) in ser.fields.iter().enumerate() {
        println!(
            "  [{i}] {:<40} type={:<40} bc={:?} enc={:?} => {:?}{}",
            f.var_name,
            f.var_type,
            f.bit_count,
            f.var_encoder,
            f.metadata.decoder,
            f.field_serializer
                .as_ref()
                .map(|s| format!("  (nested: {} fields)", s.fields.len()))
                .unwrap_or_default(),
        );
    }
}
