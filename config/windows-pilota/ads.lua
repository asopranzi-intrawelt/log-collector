local function field(value)
  if value == nil then return "-" end
  local text = tostring(value):gsub("[%c]", " ")
  if text == "" then return "-" end
  return text
end

function ads(tag, ts, record)
  local data = record["EventData"]
  if type(data) ~= "table" then data = {} end
  record["message"] = string.format(
    "user=%q event=%q logon_type=%q system=%q src_ip=%q time=%q record_id=%q",
    field(data["TargetUserName"] or data["SubjectUserName"]),
    field(record["EventID"]),
    field(data["LogonType"]),
    field(record["Computer"]),
    field(data["IpAddress"]),
    field(record["TimeCreated"]),
    field(record["EventRecordID"])
  )
  return 2, ts, record
end
