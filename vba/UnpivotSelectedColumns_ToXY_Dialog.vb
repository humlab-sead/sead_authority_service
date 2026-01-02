Option Explicit
'------------------------------------------------------------------------------
' UnpivotSelectedColumns_ToXY_Dialog
'
' This macro supports the SEAD data-reconciliation workflow in Excel.
'
' In many reconciliation sheets, several columns contain similar types of
' information (e.g. countries, place names, farms, or other geographic /
' contextual entities). These columns must be reconciled together, but their
' column names still indicate the *type* or *category* the value belongs to.
'
' The macro takes the user’s selected column(s) and “unpivots” them into a
' two-column X/Y structure:
'
'   X = the data value from the cell
'   Y = the header of the column the value came from
'
' This allows heterogeneous but related fields to be merged into a single list
' while still retaining their original semantic category (via the header text),
' which is necessary for SEAD reconciliation.
'
' The macro:
'   • Prompts for a name for the output sheet.
'   • Creates the sheet (replacing an existing sheet with the same name).
'   • Extracts all non-empty values under each selected column header.
'   • Builds an X/Y output table where each row is (Value, Header).
'   • Optionally removes duplicate X/Y pairs.
'
' The result is a clean, flat list suitable for matching against controlled
' vocabularies or preparing bulk import/reconciliation tasks for SEAD.
'------------------------------------------------------------------------------

Sub UnpivotSelectedColumns_ToXY_Dialog()
    Dim sel As Range, area As Range, colRng As Range
    Dim wsOut As Worksheet
    Dim r As Long, k As Long, cnt As Long, tmpCnt As Long
    Dim v As Variant
    Dim headerText As String
    Dim sheetName As String
    Dim doDedup As VbMsgBoxResult
    
    '=== Validate selection ===
    If TypeName(Selection) <> "Range" Then
        MsgBox "Please select one or more columns first.", vbExclamation
        Exit Sub
    End If
    Set sel = Selection
    If sel.Columns.Count = 0 Then
        MsgBox "Please select one or more columns and try again.", vbExclamation
        Exit Sub
    End If
    
    '=== Ask for sheet name ===
    sheetName = InputBox("Enter a name for the new sheet:", "New Sheet Name", "Unpivot_XY")
    If Len(Trim(sheetName)) = 0 Then
        MsgBox "Operation cancelled (no sheet name provided).", vbInformation
        Exit Sub
    End If
    
    '=== Ask whether to remove duplicates ===
    doDedup = MsgBox("Do you want to remove duplicates after unpivoting?", _
                     vbYesNo + vbQuestion, "Remove duplicates?")
    
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    '=== Create/replace output sheet ===
    On Error Resume Next
    Application.DisplayAlerts = False
    Worksheets(sheetName).Delete
    Application.DisplayAlerts = True
    On Error GoTo 0
    
    Set wsOut = Worksheets.Add
    wsOut.Name = sheetName
    wsOut.Range("A1").Value = "X"
    wsOut.Range("B1").Value = "Y"
    
    '=== Count non-empty cells across selection ===
    cnt = 0
    For Each area In sel.Areas
        For Each colRng In area.Columns
            headerText = CStr(colRng.Cells(1, 1).Value)
            v = colRng.Offset(1, 0).Resize(colRng.Rows.Count - 1).Value
            If IsArray(v) Then
                For r = 1 To UBound(v, 1)
                    If LenB(CStr(v(r, 1))) > 0 Then cnt = cnt + 1
                Next r
            Else
                If LenB(CStr(v)) > 0 Then cnt = cnt + 1
            End If
        Next colRng
    Next area
    
    If cnt = 0 Then
        MsgBox "No data found under the selected headers.", vbInformation
        GoTo Cleanup
    End If
    
    '=== Fill result array ===
    Dim res() As Variant
    ReDim res(1 To cnt, 1 To 2)
    k = 1
    
    For Each area In sel.Areas
        For Each colRng In area.Columns
            headerText = CStr(colRng.Cells(1, 1).Value)
            v = colRng.Offset(1, 0).Resize(colRng.Rows.Count - 1).Value
            If IsArray(v) Then
                For r = 1 To UBound(v, 1)
                    If LenB(CStr(v(r, 1))) > 0 Then
                        res(k, 1) = v(r, 1)       ' X
                        res(k, 2) = headerText    ' Y
                        k = k + 1
                    End If
                Next r
            Else
                If LenB(CStr(v)) > 0 Then
                    res(k, 1) = v
                    res(k, 2) = headerText
                    k = k + 1
                End If
            End If
        Next colRng
    Next area
    
    '=== Write result to new sheet ===
    wsOut.Range("A2").Resize(cnt, 2).Value = res
    wsOut.Columns("A:B").AutoFit
    
    '=== Deduplicate if user selected "Yes" ===
    If doDedup = vbYes Then
        wsOut.Range("A1").CurrentRegion.RemoveDuplicates Columns:=Array(1, 2), Header:=xlYes
    End If
    
    MsgBox "Done! Data written to sheet '" & sheetName & "'.", vbInformation
    
Cleanup:
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
End Sub


