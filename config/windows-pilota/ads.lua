local function field(value)
  if value == nil then return "-" end
  local text = tostring(value):gsub("[%c]", " ")
  if text == "" then return "-" end
  return text
end

function ads(tag, ts, record)
  local data = record["EventData"]
  if type(data) ~= "table" then data = {} end
  local event_id = tonumber(record["EventID"])
  local target = field(data["TargetUserName"])
  local subject = field(data["SubjectUserName"])
  local user = target
  if event_id == 4648 or event_id == 4672 or event_id == 1102 or
     event_id == 4719 or event_id == 4720 or event_id == 4732 or event_id == 4733 then
    user = subject
  end
  if user == "-" then
    if target ~= "-" then user = target else user = subject end
  end
  local message = string.format(
    "user=%q event=%q logon_type=%q system=%q src_ip=%q time=%q record_id=%q",
    user,
    field(record["EventID"]),
    field(data["LogonType"]),
    field(record["Computer"]),
    field(data["IpAddress"]),
    field(record["TimeCreated"]),
    field(record["EventRecordID"])
  )
  if target ~= "-" and target ~= user then
    message = message .. string.format(" target_user=%q", target)
  end
  record["message"] = message
  return 2, ts, record
end
