# Azure Durable Entities – Quick Notes

- **Entity functions**: single-threaded, addressable by ID, persistent state across calls; same semantics AWS now offers.
- **Comparison edge**: Azure requires explicit entity function; AWS uses plain Lambda + SDK decorators, reducing boiler-plate.
