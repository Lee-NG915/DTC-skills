#!/usr/bin/env ruby
# Repository-local checks; only the JSON Schema keywords used by this contract are supported.
require 'json'
require 'yaml'
require 'pathname'
ROOT = Pathname.new(__dir__).parent.expand_path

def validate(value, rule, location)
  types = {'object'=>Hash, 'array'=>Array, 'string'=>String, 'integer'=>Integer}
  raise "#{location}: unsupported type" if rule['type'] && !types.key?(rule['type'])
  raise "#{location}: wrong type" if rule['type'] && !value.is_a?(types.fetch(rule['type']))
  raise "#{location}: const mismatch" if rule.key?('const') && value != rule['const']
  if value.is_a?(String)
    raise "#{location}: too short" if rule['minLength'] && value.length < rule['minLength']
    raise "#{location}: too long" if rule['maxLength'] && value.length > rule['maxLength']
    raise "#{location}: pattern mismatch" if rule['pattern'] && !(Regexp.new(rule['pattern']) =~ value)
  end
  if value.is_a?(Hash)
    (rule['required'] || []).each { |k| raise "#{location}: missing #{k}" unless value.key?(k) }
    properties = rule.fetch('properties', {})
    if rule['additionalProperties'] == false
      raise "#{location}: unknown fields" unless (value.keys - properties.keys).empty?
    end
    properties.each { |k,v| validate(value[k], v, "#{location}.#{k}") if value.key?(k) }
  end
  if value.is_a?(Array)
    raise "#{location}: duplicates" if rule['uniqueItems'] && value.uniq != value
    value.each_with_index { |v,i| validate(v,rule['items'],"#{location}[#{i}]") } if rule['items']
  end
end

begin
  schema = JSON.parse((ROOT/'schemas/skill.schema.json').read)
  folders = (ROOT/'skills').children.select(&:directory?).sort
  raise 'No skills found' if folders.empty?
  names = folders.map { |p| p.basename.to_s }
  folders.each do |folder|
    skill = folder/'SKILL.md'
    text = skill.read
    match = text.match(/\A---\r?\n(.*?)\r?\n---\r?\n/m)
    raise "#{skill}: missing frontmatter" unless match
    fm = YAML.safe_load(match[1])
    raise "#{skill}: invalid name" unless fm.is_a?(Hash) && fm['name'] == folder.basename.to_s && fm['name'].match(/\A[a-z0-9]+(?:-[a-z0-9]+)*\z/) && fm['name'].size <= 64
    raise "#{skill}: invalid description" unless fm['description'].is_a?(String) && fm['description'].size.between?(1,1024)
    data = JSON.parse((folder/'skill.json').read)
    validate(data, schema, "#{folder.basename}/skill.json")
    raise "#{folder}: identity mismatch" unless data['name'] == fm['name']
    raise "#{folder}: missing schema" unless (folder/data['$schema']).file?
    data['relatedSkills'].each { |name| raise "#{folder}: unknown related skill #{name}" unless names.include?(name) }
  end
  catalog = JSON.parse((ROOT/'skills/catalog.json').read)
  entries = catalog.fetch('skills')
  raise 'Catalog mismatch' unless entries.map { |e| e['name'] }.sort == names.sort
  entries.each do |entry|
    data = JSON.parse((ROOT/'skills'/entry['name']/'skill.json').read)
    raise 'Catalog entry mismatch' unless entry['entrypoint'] == "#{entry['name']}/SKILL.md" && entry['stage'] == data['stage']
  end
  Dir.glob((ROOT/'**/*.md').to_s).each do |file|
    File.read(file).scan(/\]\(([^)]+)\)/).flatten.each do |url|
      next if url.match(/\A(?:[a-z]+:|#)/i)
      dest = Pathname.new(file).parent.join(url.split('#').first).cleanpath
      raise "#{file}: missing or external local reference #{url}" unless dest.to_s.start_with?(ROOT.to_s + '/') && dest.exist?
    end
  end
  puts "PASS: #{names.length} skills; frontmatter, metadata, catalog, related skills and local links"
rescue StandardError => e
  warn "FAIL: #{e.message}"
  exit 1
end
