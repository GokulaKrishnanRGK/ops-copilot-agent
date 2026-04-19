output "zone_id" {
  description = "Cloudflare zone ID."
  value       = data.cloudflare_zone.this.id
}
